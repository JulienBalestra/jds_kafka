#!/usr/bin/env bash

export DEBIAN_FRONTEND=noninteractive
export ARCH=amd64
export DISTRO="jessie"

FATHER_DEPS="ca-certificates python3 debootstrap git python python-dev build-essential libsystemd-dev pkgconf"
export CHILD_DEPS="python"

FATHER_ROOTFS="father_rootfs"
export CHILD_ROOTFS="/tmp/child_rootfs"

set -exh

if [[ $EUID -ne 0 ]]
then
   echo "This script must be run as root" 1>&2
   exit 1
fi

chroot --version
debootstrap --version

mkdir -v ${FATHER_ROOTFS}

debootstrap \
    --arch ${ARCH} \
    --variant=minbase \
    --components=main \
    --include="${FATHER_DEPS}" \
    ${DISTRO} \
    ${FATHER_ROOTFS} \
    ${DEBIAN_MIRROR} # ENV

rm -rf ${FATHER_ROOTFS}/var/cache/apt/archives/*

export DEBIAN_MIRROR
export PROXY

cp -v child.sh ${FATHER_ROOTFS}/opt/child.sh
cp -v entrypoint.sh ${FATHER_ROOTFS}/opt/entrypoint.sh
cp -vR app ${FATHER_ROOTFS}/app

mount -o bind /dev ${FATHER_ROOTFS}/dev/
mount -t sysfs sysfs ${FATHER_ROOTFS}/sys/
mount -t proc proc ${FATHER_ROOTFS}/proc/

set +e

chroot ${FATHER_ROOTFS} \
    env HOME=/opt \
    /opt/child.sh

umount ${FATHER_ROOTFS}/dev/
umount ${FATHER_ROOTFS}/sys/
umount ${FATHER_ROOTFS}/proc/
