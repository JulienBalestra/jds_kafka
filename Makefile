all: rootfs

rootfs: family
	mv father_rootfs/child_rootfs rootfs

family: 
	./father.sh

clean:
	rm -Rf father_rootfs

fclean: clean
	rm -Rf rootfs
	acbuild --debug end

re: fclean rootfs

aci:
	acbuild --debug begin
	rm -Rf .acbuild/currentaci/rootfs/
	mv rootfs .acbuild/currentaci/
	acbuild --debug set-name jds_kafka
	acbuild --debug set-exec -- /entrypoint.sh
	acbuild --debug environment add PATH /opt/env/bin:$PATH
	acbuild --debug environment add JDS /opt/app/jds_kafka.py
	acbuild --debug write --overwrite jds_kafka.aci
	acbuild --debug end


.PHONY: build clean
