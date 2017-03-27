#!/bin/bash
set -eu

echo "Running interop.sh"
export VIRTHOST=$(head $WORKSPACE/product/undercloud.yaml | cut -d" " -f2)
export INFRARED_DIR=$(head $WORKSPACE/product/interop_data/osp_interop_output.yaml | cut -d" " -f2)
export HW_ENV_DIR=$WORKSPACE
echo "dns_server: 10.11.5.19" > $HW_ENV_DIR/all.yml
echo "disable_ssh_dns: true" >> $HW_ENV_DIR/all.yml
echo "browbeat_pub_subnet: 192.168.20.0/22" >> $HW_ENV_DIR/all.yml
echo "browbeat_pub_pool_start: 192.168.21.71" >> $HW_ENV_DIR/all.yml
echo "browbeat_pub_pool_end: 192.168.21.80" >> $HW_ENV_DIR/all.yml
echo "browbeat_pub_pool_gw: 192.168.23.254" >> $HW_ENV_DIR/all.yml
echo "browbeat_pri_pool_dns: 192.168.5.19" >> $HW_ENV_DIR/all.yml

export OPT_DEBUG_ANSIBLE=0
export PLAYBOOK=interop-browbeat.yml
export VARS="elastic_enabled_template=true \
--extra-vars grafana_enabled_template=false \
--extra-vars elastic_host_template=elk.browbeatproject.org \
--extra-vars browbeat_cloud_name=iits \
--extra-vars graphite_prefix_template=iits"

#used to ensure concurrent jobs on the same executor work
socketdir=$(mktemp -d /tmp/sockXXXXXX)
export ANSIBLE_SSH_CONTROL_PATH=$socketdir/%%h-%%r

set +u
virtualenv $WORKSPACE
source $WORKSPACE/bin/activate
set -u
curl https://raw.githubusercontent.com/openstack/tripleo-quickstart/master/ansible.cfg > $WORKSPACE/ansible.cfg
mkdir $WORKSPACE/playbooks
echo "[undercloud]" > $WORKSPACE/hosts
echo "undercloud-0" >> $WORKSPACE/hosts
pip install crudini
pip install file://$WORKSPACE/git_sources/browbeat/#egg=browbeat
export ANSIBLE_CONFIG=$WORKSPACE/ansible.cfg
echo "ssh_args = -F ansible.ssh.config" >> $WORKSPACE/ansible.cfg
pushd $INFRARED_DIR
ansible-playbook -i $WORKSPACE/hosts $WORKSPACE/playbooks/interop-browbeat.yml

