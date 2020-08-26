cd %~dp0

:: 本地构建 - 依赖 : setuptools wheel 
:: setup.py文件编写详见 - 
python setup.py sdist bdist_wheel

:: 上传包 -- 依赖 : python -m pip install --upgrade twine
:: 用户名密码在 home\.pypirc 没有手动
pause 按任意键上传到 pypi ...
python -m twine upload dist/*

pause