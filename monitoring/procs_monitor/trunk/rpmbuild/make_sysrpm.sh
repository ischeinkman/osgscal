#!/bin/bash
NAME='procs_monitor_syslogger'
VERSION=${1:-0.1}
RELEASE=${2:-1}

ROOT_DIR="$(dirname $0)/.."

TMP_DIR=${NAME}-${VERSION}

mkdir -p $TMP_DIR
cp $ROOT_DIR/bin/syslogger.py $TMP_DIR
cp $ROOT_DIR/etc/osg_log_rotate $TMP_DIR
cp $ROOT_DIR/etc/procs_to_watch.conf $TMP_DIR
cp $ROOT_DIR/rpmbuild/syslogger.spec $TMP_DIR

tar -czvf ${NAME}-${VERSION}.tgz ${NAME}-${VERSION}/

mkdir -p RPMBUILD/{RPMS/noarch,SPECS,BUILD,SOURCES,SRPMS}
rpmbuild --define "_topdir `pwd`/RPMBUILD" \
         --define "ver ${VERSION}"         \
         --define "rel ${RELEASE}"         \
         --define "name ${NAME}"           \
         -tb ./${NAME}-${VERSION}.tgz

find RPMBUILD/ -type f -name "*.rpm" -exec mv {} . \;
rm -rf RPMBUILD/ ${NAME}-${VERSION}/ ./${NAME}-${VERSION}.tgz
