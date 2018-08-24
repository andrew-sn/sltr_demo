# encoding: utf-8
from urllib.parse import urljoin
import requests
import json
import re
from collections import defaultdict
import pdb
import os

from index_utils import *


ES_HOST = 'http://localhost:9200'


class Judgment:
    """记录标注数据的类，每一行标注数据转化为一个实例"""
    def __init__(self, grade, qid, keywords, doc_id):
        self.grade = grade
        self.qid = qid
        self.keywords = keywords
        self.doc_id = doc_id
        # 该属性是用来记录`score`的，0th feature is ranklib feature 1
        self.features = []

    def __str__(self):
        return "grade:%s qid:%s (%s) docid:%s" % (self.grade, self.qid, self.keywords, self.docId)

    def to_ranklib_format(self):
        features_as_strs = ["%s:%s" % (idx+1, feature) for idx, feature in enumerate(self.features)]
        comment = "# %s\t%s" % (self.doc_id, self.keywords)
        return "%s\tqid:%s\t%s %s" % (self.grade, self.qid, "\t".join(features_as_strs), comment)


def _queries_from_header(lines):
    """ Parses out mapping between, query id and user keywords
        from header comments, ie:
        # qid:523: First Blood
        returns dict mapping all query ids to search keywords"""
    # Regex can be debugged here:
    # http://www.regexpal.com/?fam=96564
    regex = re.compile('#\sqid:(\d+?):\s+?(.*)')
    r_val = {}
    for line in lines:
        if line[0] != '#':
            break
        m = re.match(regex, line)
        if m:
            r_val[int(m.group(1))] = m.group(2)
    return r_val


def _judgments_from_body(lines):
    """ Parses out judgment/grade, query id, and docId in line such as:
         4  qid:523   # a01  Grade for Rambo for query Foo
        <judgment> qid:<queryid> # docId <rest of comment ignored...)"""
    # Regex can be debugged here:
    # http://www.regexpal.com/?fam=96565
    regex = re.compile('^(\d)\s+qid:(\d+)\s+#\s+(\w+).*')
    for line in lines:
        m = re.match(regex, line)
        if m:
            # print("%s,%s,%s" % (m.group(1), m.group(2), m.group(3)))
            yield int(m.group(1)), int(m.group(2)), m.group(3)


def create_feature_store():
    feature_store_name = '_ltr'
    path = urljoin(ES_HOST, feature_store_name)
    # 创建前先删除
    print("DELETE %s" % path)
    resp = requests.delete(path)
    print("%s" % resp.status_code)
    # 创建
    print("PUT %s" % path)
    resp = requests.put(path)
    print("%s" % resp.status_code)


def create_feature_set():
    feature_set_name = 'movie_features'
    feature_set = {
        'featureset': {
            'name': feature_set_name,
            'features': [
                # {
                #     # 在`Ranklib`中`features`是根据顺序来辨别的，因此使用`1`
                #     'name': '1',
                #     'params': ['keywords'],
                #     'template': {
                #         'match': {
                #             'title': '{{keywords}}'
                #         }
                #     }
                # },
                {
                    'name': '1',
                    'params': ['keywords'],
                    'template': {
                        'match': {
                            'overview': '{{keywords}}'
                        }
                    }
                }
            ]
        }
    }
    path = '_ltr/_featureset/{}'.format(feature_set_name)
    full_path = urljoin(ES_HOST, path)
    print("POST %s" % full_path)
    head = {'Content-Type': 'application/json'}
    resp = requests.post(full_path, data=json.dumps(feature_set), headers=head)
    print(json.dumps(feature_set))
    print("%s" % resp.status_code)
    print("%s" % resp.text)


def create_training_data(input_file_name, output_file_name):
    # 整理标注数据后的结果
    r_val = defaultdict(list)
    r_judge = []

    # 基于标注文件生成query_id与query对
    with open(input_file_name) as f:
        qid2keywords = _queries_from_header(f)
    with open(input_file_name) as f:
        for grade, qid, doc_id in _judgments_from_body(f):
            r_judge.append(Judgment(grade=grade, qid=qid, keywords=qid2keywords[qid], doc_id=doc_id))
    for judge in r_judge:
        r_val[judge.qid].append(judge)

    # 用于记录`feature`结果的`query`
    log_query = {
        "size": 10000,
        "query": {
            "bool": {
                "filter": [
                    {
                        "terms": {
                            "_id": []

                        }
                    }
                ],
                "should": [
                    {"sltr": {
                        "_name": "logged_featureset",
                        "featureset": "movie_features",
                        "params": {
                            "keywords": ""
                        }
                    }}
                ]
            }
        },
        "ext": {
            "ltr_log": {
                "log_specs": {
                    "name": "main",
                    "named_query": "logged_featureset",
                    "missing_as_zero": True

                }
            }
        }
    }
    # 获取`feature`的`score`，按照`query`向`es`发起请求
    for qid, judges in r_val.items():
        keywords = judges[0].keywords
        doc_ids = [judge.doc_id for judge in judges]
        log_query['query']['bool']['filter'][0]['terms']['_id'] = doc_ids
        log_query['query']['bool']['should'][0]['sltr']['params']['keywords'] = keywords
        res = search_es('tmdb', log_query)
        # 从`es`返回的结果中将`feature`的`score`记录下来，供日后训练使用
        r_es = {}
        for doc in res['hits']['hits']:
            doc_id = doc['_id']
            features = doc['fields']['_ltrlog'][0]['main']
            r_es[doc_id] = [_['value'] for _ in features]
        for judge in r_judge:
            try:
                judge.features = r_es[judge.doc_id]
            except KeyError:
                # 表明结果中没有该`id`，个人认为分数应该置0，`es`返回最大结果是10000条记录
                print("Missing doc_id %s" % judge.doc_id)

    # 记录带有`feature`分数的结果
    with open(output_file_name, 'w') as f:
        for qid, judges in r_val.items():
            for judge in judges:
                f.write(judge.to_ranklib_format() + "\n")


def train_model(train_data_file, model_file):
    for model in range(10):
        if model != 0:
            continue
        print('使用模型:{}'.format(model))
        # 0, MART
        # 1, RankNet
        # 2, RankBoost
        # 3, AdaRank
        # 4, coord Ascent
        # 6, LambdaMART
        # 7, ListNET
        # 8, Random Forests
        # 9, Linear Regression
        # java -jar RankLib-2.6.jar -ranker model -train sample_judgments_with_score.txt -save model.txt
        cmd = "java -jar /data/home/liusunan/es/ltr_test/ranklib_test/RankLib-2.8.jar -ranker %s -train %s -save %s -frate 1.0" % (
            model, train_data_file, model_file)
        print("Running %s" % cmd)
        os.system(cmd)


def save_moedl2es(script_name, feature_set, model_file):
    """
    目前支持的"type":
    1. ranklib: model / ranklib
    2. xgboost: model / xgboost + json
    3. simple dot product: model / linear
    """
    model_payload = {
        "model": {
            "name": script_name,
            "model": {
                "type": "model/ranklib",
                "definition": {
                }
            }
        }
    }
    with open(model_file) as f:
        model_content = f.read()
        path = "_ltr/_featureset/%s/_createmodel" % feature_set
        full_path = urljoin(ES_HOST, path)
        print("POST %s" % full_path)
        model_payload['model']['model']['definition'] = model_content
        head = {'Content-Type': 'application/json'}
        resp = requests.post(full_path, data=json.dumps(model_payload), headers=head)
        print(resp.status_code)
        if resp.status_code >= 300:
            print(resp.text)


if __name__ == "__main__":
    # 创建`feature store`
    print('{0}开始创建feature store{0}'.format('*'*10))
    create_feature_store()

    # 创建`feature set`
    print('{0}开始创建feature set{0}'.format('*'*10))
    create_feature_set()

    # 在标注数据基础上，结合`feature set`生成训练数据
    print('{0}开始生成训练数据{0}'.format('*' * 10))
    create_training_data('/data/home/liusunan/es/ltr_test/ranklib_test/sample_judgments.txt',
                         '/data/home/liusunan/es/ltr_test/ranklib_test/sample_judgments_with_score.txt')

    # 使用`ranklib`进行训练
    print('{0}开始训练模型{0}'.format('*' * 10))
    train_model('/data/home/liusunan/es/ltr_test/ranklib_test/sample_judgments_with_score.txt',
                '/data/home/liusunan/es/ltr_test/ranklib_test/model.txt')

    # 将模型训练存入es中
    print('{0}将训练好的模型存入es{0}'.format('*' * 10))
    save_moedl2es('model_0', 'movie_features', '/data/home/liusunan/es/ltr_test/ranklib_test/model.txt')
