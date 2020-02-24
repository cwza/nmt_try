# nmt_try
> My experients of nmt


## Editable Install

``` sh
git clone this repository
make install
```

## Develop

1. Modify notebooks in nbs folder (Write unit tests in the same notebook and create new notebook to write integration test)
2. `nbdev_build_lib` to update python files
3. `make test` to run unit test
4. `make test-slow` to run integration test
5. `make build-all` to run build-lib, build-docs, clean-nbs
6. `git add commit and push`

## Data

If you want to run 95_nc_xxx.ipynb, do following:

1. Download http://data.statmt.org/news-commentary/v14/training/news-commentary-v14.en-zh.tsv.gz
2. Unzip and save it to `./nbs/data/News_Commentary/news-commentary-v14.en-zh.tsv`
3. Run 02_data.news_commentary.ipynb to generate tok-news-commentary-v14.en-zh.csv in ./nbs/data/News_Commentary/
