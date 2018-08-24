# encoding: utf-8
from index_utils import *
import json
import pdb

mapping = '''
{
    "settings" : {
        "index": {
            "number_of_shards" : 3,
            "number_of_replicas" : 2
        }
    },
    "mappings":{
        "sources": {
            "properties": {
                "adult":{
                    "type": "boolean"             
                }, 
                "original_language":{
                    "type": "keyword",
                    "index": "true"
                },
                "original_title":{
                    "type": "text",
                    "index": "true"
                }, 
                "overview":{
                    "type": "text",
                    "index": "true"
                },
                "popularity":{
                    "type": "float"
                },
                "runtime":{
                    "type": "short"
                },
                "tagline":{
                    "type": "text",
                    "index": "true"
                },
                "vote_average":{
                    "type": "float"
                } 
            }
        }
    }        
}'''


def pre_process(source):
    for id, item in source.items():
        try:
            del item['release_date']
        except KeyError:
            pass
    return source


if __name__ == "__main__":
    # 创建`index`
    # create_index('tmdb', mapping)

    # 插入数据
    movieDict = json.load(open('/data/home/liusunan/es/ltr_test/ranklib_test/tmdb.json'))
    print('{}load data finish{}'.foramt('*'*10))
    movieDict = pre_process(movieDict)
    data2es('tmdb', 'sources', movieDict)
