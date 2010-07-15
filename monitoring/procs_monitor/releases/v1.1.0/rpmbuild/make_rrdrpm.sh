#!/bin/bash
NAME='procs_monitor_rrdlogger'
VERSION=${1:-0.1}
RELEASE=${2:-1}

ROOT_DIR="$(dirname $0)/.."

TMP_DIR=${NAME}-${VERSION}

mkdir -p $TMP_DIR
cp $ROOT_DIR/bin/rrdlogger.py $TMP_DIR
cp $ROOT_DIR/etc/rrdlogger.conf $TMP_DIR
cp $ROOT_DIR/rpmbuild/rrdlogger.spec $TMP_DIR
cp $ROOT_DIR/LICENSE $TMP_DIR

sed -i 's|^#\(.*\)\$PROC_MON|\1/var/lib/procs_monitor|g' $TMP_DIR/rrdlogger.conf

tar -czvf ${NAME}-${VERSION}.tgz ${NAME}-${VERSION}/

mkdir -p RPMBUILD/{RPMS/noarch,SPECS,BUILD,SOURCES,SRPMS}
rpmbuild --define "_topdir `pwd`/RPMBUILD" \
         --define "ver ${VERSION}"         \
         --define "rel ${RELEASE}"         \
         --define "name ${NAME}"           \
         -tb ./${NAME}-${VERSION}.tgz

find RPMBUILD/ -type f -name "*.rpm" -exec mv {} . \;
rm -rf RPMBUILD/ ${NAME}-${VERSION}/ ./${NAME}-${VERSION}.tgz
