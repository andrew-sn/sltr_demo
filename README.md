# sltr_demo
这个是o19s提供的[elasticsearch-learning-to-rank](https://github.com/o19s/elasticsearch-learning-to-rank)插件的demo

原版demo中记录了两个feature，这给最后效果的展示带来一定的干扰，因此这里对原版demo稍作修改，以期直观得展示出该插件的效果

## 使用步骤
1. prepare.py 

下载RankLib.jar与tmdb.json，前者供训练模型使用，后者是数据集

2. create_insert.py

创建`index`并将`tmdbs.json`插入

3. train.py

* 创建`feature store`，`PUT http://localhost:9200/_ltr`，其中`_ltr`为`feature store name`

* 创建`feature set`，`POST http://localhost:9200/_ltr/_featureset/movie_features`，其中`movie_features`为`feature set name`

* 在之前创建的`feature set`上进行`log features`，结合标注数据`sample_judgements.txt`，生成最终的训练数据`sample_judgements_with_score.txt`

* 使用`sample_judgements_with_score.txt`训练生成模型文件`model.txt`，并将模型插入`es`

4. search.py

使用`sltr`语句进行搜索

## 最后
es7.0之后将不支持mapping_types的功能，估计o19s又有个大活干了；

感谢开源
