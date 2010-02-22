#!/bin/bash
NAME='procs_monitor'
VERSION=${1:-0.1}
RELEASE=${2:-1}

ROOT_DIR="$(dirname $0)/.."

TMP_DIR=${NAME}-${VERSION}

mkdir -p $TMP_DIR
cp $ROOT_DIR/bin/proc_collector.pl $TMP_DIR
cp $ROOT_DIR/lib/* $TMP_DIR
cp $ROOT_DIR/etc/osgmonitoring.conf $TMP_DIR
cp $ROOT_DIR/etc/procs_to_watch.conf $TMP_DIR
cp $ROOT_DIR/rpmbuild/proc_mon.spec $TMP_DIR

sed -i -e 's|^#\(procs_conf = \)\$PROC_MON/etc|\1/etc/procs_monitor|g' -e 's|^#\(out_file = \)\$PROC_MON|\1/var/lib/procs_monitor|g' $TMP_DIR/osgmonitoring.conf 

echo "#!/bin/bash" > $TMP_DIR/osgmon_cron.sh
echo "/usr/local/libexec/procs_monitor/proc_collector.pl /etc/procs_monitor/osgmonitoring.conf" >> $TMP_DIR/osgmon_cron.sh
echo "*/5 * * * * root /usr/local/libexec/procs_monitor/osgmon_cron.sh" > $TMP_DIR/proc_mon.cron

tar -czvf ${NAME}-${VERSION}.tgz ${NAME}-${VERSION}/

mkdir -p RPMBUILD/{RPMS/noarch,SPECS,BUILD,SOURCES,SRPMS}
rpmbuild --define "_topdir `pwd`/RPMBUILD" \
         --define "ver ${VERSION}"         \
         --define "rel ${RELEASE}"         \
         --define "name ${NAME}"           \
         -tb ./${NAME}-${VERSION}.tgz

find RPMBUILD/ -type f -name "*.rpm" -exec mv {} . \;
rm -rf RPMBUILD/ ${NAME}-${VERSION}/ ./${NAME}-${VERSION}.tgz
