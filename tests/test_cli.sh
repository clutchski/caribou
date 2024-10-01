set -e

# this doesn't validate output but is a quick spotcheck to make sure
# the documented cli works

d=tmp_test_cli
db=test_cli.sqlite
m=test_cli_migration_marker

mkdir -p $d

export PYTHONPATH=$PYTHONPATH:caribou

cli="python caribou/cli.py"

$cli -h
$cli version $db

$cli create -d $d $m
$cli upgrade $db $d
$cli version $db
$cli downgrade $db $d 0
$cli version $db
$cli upgrade $db $d
$cli version $db
$cli list $d

rm -rf $d $db
rm -f "*$m*"


echo "==========================="
echo " cli tests passed"
echo "==========================="
