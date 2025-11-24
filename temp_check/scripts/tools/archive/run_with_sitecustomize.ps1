$env:PYTHONPATH = ".;" + $env:PYTHONPATH
Write-Host "[sitecustomize] PYTHONPATH=$env:PYTHONPATH"
python $args
