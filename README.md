# nmt_try
> My experience of nmt


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
