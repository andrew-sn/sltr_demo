# encoding:utf-8
from index_utils import *
import pdb
from pprint import pprint

baseQuery = {
  "query": {
      "multi_match": {
          "query": "",
          "fields": ["overview"]
       }
   },
  "rescore": {
      "query": {
        "rescore_query": {
            "sltr": {
                "params": {
                    "keywords": ""
                },
                "model": "",
            }
         },
        "query_weight": 0.001,
        "rescore_query_weight": 2
      }
   }
}
baseQuery_v2 = {
  "query": {
      "multi_match": {
          "query": "rambo",
          "fields": ["overview"]
       }
   }
}
baseQuery['explain'] = 'true'


def ltr_query(query, model_name):
    import json
    baseQuery['rescore']['query']['rescore_query']['sltr']['model'] = model_name
    baseQuery['query']['multi_match']['query'] = query
    baseQuery['rescore']['query']['rescore_query']['sltr']['params']['keywords'] = query
    # return baseQuery_v2
    return baseQuery


def search_query(query, model_name, index):
    return search_es(index, ltr_query(query, model_name))


if __name__ == "__main__":
    res = search_query('rambo', 'model_0', 'tmdb')
    for result in res['hits']['hits']:
        print(result['_source']['title'] + ' ' + str(result['_source']['id']))
