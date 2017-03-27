#!/usr/bin/env python
import ci_interop_util
import shutil
import yaml

args = ci_interop_util.parse_interop_args()
output_dir = args['data_out']
openstack_config_file = os.path.join(output_dir, 'osp_interop_output.yaml')

with open(openstack_config_file) as f:
        os_config = yaml.safe_load(f)

inventory_file_name = 'hosts'
infrared_dir = os_config['infrared_directory']
inventory_src = os.path.join(infrared_dir, inventory_file_name)
shutil.copyfile(inventory_src, inventory_file_name)
