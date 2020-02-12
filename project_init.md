## Install nbdev and Clone nbdev_template
``` bash
pip3 install nbdev
git clone https://github.com/fastai/nbdev_template.git
mkdir nbs
mv 00_core.ipynb nbs
mv index.ipynb nbs
```

## Edit settings.ini
```
lib_name = nmt_try
user = cwza
description = My experiments of nmt
keywords = seq2seq transformer nmt
author = cwza
author_email = cwz0205a@gmail.com
copyright = cwza

nbs_path = nbs
tst_flags = slow|skip
```

## Edit setup.py
``` python
# requirements = cfg.get('requirements','').split()
setuptools.setup(
    # install_requires = requirements,
    install_requires = [
        'fastai2 @ git+https://github.com/fastai/fastai2.git',
    ],
    extras_require={
        'dev': ['nbdev']
    },
```


## Add Makefile
```
install:
	pip3 install -e ".[dev]"

uninstall:
	python3 setup.py develop --uninstall

test:
	nbdev_test_nbs --timing=true

test-slow:
	nbdev_test_nbs --flags=slow --timing=true

build-all:
	nbdev_build_lib
	rm -f ./docs/*.html
	nbdev_build_docs --force_all=true
	nbdev_trust_nbs
	nbdev_clean_nbs
```

## Generate root package and Add git hooks for nb clean
``` bash
nbdev_build_lib
nbdev_install_git_hooks
```

## Install
``` bash
make install
```

## Develop
1. Modify notebooks in nbs folder (Write unit tests in the same notebook and create new notebook to write integration test)
2. `nbdev_build_lib` to update python files
3. `make test` to run unit test
4. `make test-slow` to run integration test
5. `make build-all` to run build-lib, build-docs, clean-nbs
6. `git add commit and push`
