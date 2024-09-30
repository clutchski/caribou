set -e

# this doesn't validate output but is a quick spotcheck to make sure
# the documented cli works

d=tmp_test_cli
db=test_cli.sqlite
m=test_cli_migration_marker

mkdir -p $d

caribou -h
caribou version $db

caribou create -d $d $m
caribou upgrade $db $d
caribou version $db
caribou downgrade $db $d 0
caribou version $db
caribou upgrade $db $d
caribou version $db
caribou list $d

rm -rf $d $db
rm -f "*$m*"


echo "cli commands didn't fail"
