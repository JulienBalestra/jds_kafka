#!/usr/bin/env bash

CHILD_ROOTFS=/child_rootfs
PYTHON_SYSD=python-systemd
REPO=https://github.com/systemd/python-systemd.git
ENV=/opt/env

cd

set -exh

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python-virtualenv

set +x
if [[ $PROXY ]]
then
    echo "config --global http.proxy PROXY"
    git config --global http.proxy $PROXY
    set -x
fi

git clone ${REPO} ${PYTHON_SYSD}
make -C ${PYTHON_SYSD}

mkdir -v ${CHILD_ROOTFS}
debootstrap \
    --arch ${ARCH} \
    --variant=minbase \
    --components=main \
    --include="${CHILD_DEPS}" \
    ${DISTRO} \
    ${CHILD_ROOTFS} \
    ${DEBIAN_MIRROR}

rm -rf ${CHILD_ROOTFS}/var/cache/apt/archives/*

DESTDIR=${CHILD_ROOTFS} make -C ${PYTHON_SYSD} install
virtualenv ${CHILD_ROOTFS}${ENV} --system-site-packages

mv -v /app ${CHILD_ROOTFS}/opt
mv -v /opt/entrypoint.sh ${CHILD_ROOTFS}/entrypoint.sh

set +x
if [[ $PROXY ]]
then
    echo "${CHILD_ROOTFS}${ENV}/bin/pip --proxy PROXY install kafka-python --upgrade"
    ${CHILD_ROOTFS}${ENV}/bin/pip --proxy $PROXY \
        install -r ${CHILD_ROOTFS}/opt/app/requirements.txt --upgrade
    set -x
else
    set -x
    ${CHILD_ROOTFS}${ENV}/bin/pip install -r ${CHILD_ROOTFS}/opt/app/requirements.txt --upgrade
fi


