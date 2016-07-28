all: rootfs

rootfs: family
	mv father_rootfs/child_rootfs rootfs

family: 
	./father.sh

clean:
	rm -Rf father_rootfs .acbuild

fclean: clean
	rm -v jds_kafka.aci

re: fclean rootfs

check: 
	SD=no PYTHONPATH=/opt/ chroot rootfs/ /opt/env/bin/python -m unittest discover /opt/app/tests/

aci: 
	acbuild --debug begin
	rm -Rf .acbuild/currentaci/rootfs/
	mv rootfs .acbuild/currentaci/
	acbuild --debug set-name jds_kafka
	acbuild --debug set-exec -- /entrypoint.sh
	acbuild --debug environment add PATH '/opt/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
	acbuild --debug environment add JDS /opt/app/jds_kafka.py
	acbuild --debug write --overwrite jds_kafka.aci
	acbuild --debug end
	ls -lh jds_kafka.aci


.PHONY: rootfs family clean fclean re check aci
