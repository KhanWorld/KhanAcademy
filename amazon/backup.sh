#!/bin/sh

cd /home/ec2-user

# Backup entire datastore
google_appengine/appcfg.py download_data --application=khan-academy --url=http://khan-academy.appspot.com/remote_api --filename=`date +%F.full.dat` --log_file=`date +%F.bulkloader.full.log` --email=khanbackups@gmail.com --rps_limit=15000 --http_limit=40 --bandwidth_limit=10000000 --batch_size=500 --num_threads=55 --passin < private_pw > `date +%F.full.log`

# Gzip results
gzip -f *.full.dat
gzip -f *.full.log

for f in *.full.dat.gz
do
  echo "Splitting $f"
  split -b4000m $f $f-
done

for f in *.full.*.gz-*
do
  echo "Moving $f to s3 bucket"
  s3cmd-1.0.0/s3cmd put $f s3://KA-full-backups/$f
done

# Delete files older than 1 week
find *.gz -mtime +7 -exec rm {} \;
find *.log -mtime +7 -exec rm {} \;
find *.dat -mtime +7 -exec rm {} \;
find *.sql3 -mtime +7 -exec rm {} \;

rm bulkloader-*
