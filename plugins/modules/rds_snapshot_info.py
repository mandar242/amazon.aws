#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014-2017 Ansible Project
# Copyright (c) 2017, 2018 Will Thames
# Copyright (c) 2017, 2018 Michael De La Rue
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: rds_snapshot_info
version_added: 5.0.0
short_description: obtain information about one or more RDS snapshots
description:
  - Obtain information about one or more RDS snapshots. These can be for unclustered snapshots or snapshots of clustered DBs (Aurora).
  - Aurora snapshot information may be obtained if no identifier parameters are passed or if one of the cluster parameters are passed.
  - This module was originally added to C(community.aws) in release 1.0.0.
options:
  db_snapshot_identifier:
    description:
      - Name of an RDS (unclustered) snapshot.
      - Mutually exclusive with O(db_instance_identifier), O(db_cluster_identifier), O(db_cluster_snapshot_identifier).
    required: false
    aliases:
      - snapshot_name
    type: str
  db_instance_identifier:
    description:
      - RDS instance name for which to find snapshots.
      - Mutually exclusive with O(db_snapshot_identifier), O(db_cluster_identifier), O(db_cluster_snapshot_identifier).
    required: false
    type: str
  db_cluster_identifier:
    description:
      - RDS cluster name for which to find snapshots.
      - Mutually exclusive with O(db_snapshot_identifier), O(db_instance_identifier), O(db_cluster_snapshot_identifier).
    required: false
    type: str
  db_cluster_snapshot_identifier:
    description:
      - Name of an RDS cluster snapshot.
      - Mutually exclusive with O(db_instance_identifier), O(db_snapshot_identifier), O(db_cluster_identifier).
    required: false
    type: str
  snapshot_type:
    description:
      - Type of snapshot to find.
      - By default both automated and manual snapshots will be returned.
    required: false
    choices: ['automated', 'manual', 'shared', 'public']
    type: str
author:
  - "Will Thames (@willthames)"
extends_documentation_fragment:
  - amazon.aws.common.modules
  - amazon.aws.region.modules
  - amazon.aws.boto3
"""

EXAMPLES = r"""
- name: Get information about an snapshot
  amazon.aws.rds_snapshot_info:
    db_snapshot_identifier: snapshot_name
  register: new_database_info

- name: Get all RDS snapshots for an RDS instance
  amazon.aws.rds_snapshot_info:
    db_instance_identifier: helloworld-rds-master
"""

RETURN = r"""
cluster_snapshots:
  description: List of cluster snapshots.
  returned: always
  type: complex
  contains:
    allocated_storage:
      description: How many gigabytes of storage are allocated.
      returned: always
      type: int
      sample: 1
    availability_zones:
      description: The availability zones of the database from which the snapshot was taken.
      returned: always
      type: list
      sample:
      - ca-central-1a
      - ca-central-1b
    cluster_create_time:
      description: Date and time the cluster was created.
      returned: always
      type: str
      sample: "2018-05-17T00:13:40.223000+00:00"
    db_cluster_identifier:
      description: Database cluster identifier.
      returned: always
      type: str
      sample: "test-aurora-cluster"
    db_cluster_snapshot_arn:
      description: ARN of the database snapshot.
      returned: always
      type: str
      sample: "arn:aws:rds:ca-central-1:123456789012:cluster-snapshot:test-aurora-snapshot"
    db_cluster_snapshot_identifier:
      description: Snapshot identifier.
      returned: always
      type: str
      sample: "test-aurora-snapshot"
    engine:
      description: Database engine.
      returned: always
      type: str
      sample: "aurora"
    engine_version:
      description: Database engine version.
      returned: always
      type: str
      sample: "5.6.10a"
    iam_database_authentication_enabled:
      description: Whether database authentication through IAM is enabled.
      returned: always
      type: bool
      sample: false
    kms_key_id:
      description: ID of the KMS Key encrypting the snapshot.
      returned: always
      type: str
      sample: "arn:aws:kms:ca-central-1:123456789012:key/abcd1234-abcd-1111-aaaa-0123456789ab"
    license_model:
      description: License model.
      returned: always
      type: str
      sample: "aurora"
    master_username:
      description: Database master username.
      returned: always
      type: str
      sample: "shertel"
    percent_progress:
      description: Percent progress of snapshot.
      returned: always
      type: int
      sample: 0
    port:
      description: Database port.
      returned: always
      type: int
      sample: 0
    snapshot_create_time:
      description: Date and time when the snapshot was created.
      returned: always
      type: str
      sample: "2018-05-17T00:23:23.731000+00:00"
    snapshot_type:
      description: Type of snapshot.
      returned: always
      type: str
      sample: "manual"
    status:
      description: Status of snapshot.
      returned: always
      type: str
      sample: "creating"
    storage_encrypted:
      description: Whether the snapshot is encrypted.
      returned: always
      type: bool
      sample: true
    tags:
      description: Tags of the snapshot.
      returned: when snapshot is not shared.
      type: complex
      contains: {}
    vpc_id:
      description: VPC of the database.
      returned: always
      type: str
      sample: "vpc-abcd1234"
"""

from typing import Any
from typing import Callable
from typing import Dict
from typing import List

from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.amazon.aws.plugins.module_utils.modules import AnsibleAWSModule
from ansible_collections.amazon.aws.plugins.module_utils.rds import AnsibleRDSError
from ansible_collections.amazon.aws.plugins.module_utils.rds import describe_db_cluster_snapshots
from ansible_collections.amazon.aws.plugins.module_utils.rds import describe_db_snapshots
from ansible_collections.amazon.aws.plugins.module_utils.tagging import boto3_tag_list_to_ansible_dict


def common_snapshot_info(
    client, module: AnsibleAWSModule, describe_snapshots_method: Callable, params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    try:
        results = describe_snapshots_method(client, **params)
    except AnsibleRDSError as e:
        module.fail_json_aws(e, "Failed to get snapshot information")

    for snapshot in results:
        if snapshot["SnapshotType"] != "shared":
            snapshot["Tags"] = boto3_tag_list_to_ansible_dict(snapshot.pop("Tags", []))

    return [camel_dict_to_snake_dict(snapshot, ignore_list=["Tags"]) for snapshot in results]


def cluster_snapshot_info(client, module: AnsibleAWSModule) -> List[Dict[str, Any]]:
    snapshot_id = module.params.get("db_cluster_snapshot_identifier")
    snapshot_type = module.params.get("snapshot_type")
    instance_name = module.params.get("db_cluster_identifier")

    params = dict()
    if snapshot_id:
        params["DBClusterSnapshotIdentifier"] = snapshot_id
    if instance_name:
        params["DBClusterIdentifier"] = instance_name
    if snapshot_type:
        params["SnapshotType"] = snapshot_type
        if snapshot_type == "public":
            params["IncludePublic"] = True
        elif snapshot_type == "shared":
            params["IncludeShared"] = True

    return common_snapshot_info(client, module, describe_db_cluster_snapshots, params)


def instance_snapshot_info(client, module: AnsibleAWSModule) -> List[Dict[str, Any]]:
    snapshot_id = module.params.get("db_snapshot_identifier")
    snapshot_type = module.params.get("snapshot_type")
    instance_name = module.params.get("db_instance_identifier")

    params = dict()
    if snapshot_id:
        params["DBSnapshotIdentifier"] = snapshot_id
    if instance_name:
        params["DBInstanceIdentifier"] = instance_name
    if snapshot_type:
        params["SnapshotType"] = snapshot_type
        if snapshot_type == "public":
            params["IncludePublic"] = True
        elif snapshot_type == "shared":
            params["IncludeShared"] = True

    return common_snapshot_info(client, module, describe_db_snapshots, params)


def main():
    argument_spec = dict(
        db_snapshot_identifier=dict(aliases=["snapshot_name"]),
        db_instance_identifier=dict(),
        db_cluster_identifier=dict(),
        db_cluster_snapshot_identifier=dict(),
        snapshot_type=dict(choices=["automated", "manual", "shared", "public"]),
    )

    module = AnsibleAWSModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            [
                "db_snapshot_identifier",
                "db_instance_identifier",
                "db_cluster_identifier",
                "db_cluster_snapshot_identifier",
            ]
        ],
    )

    client = module.client("rds")
    results = dict()
    if not module.params["db_cluster_identifier"] and not module.params["db_cluster_snapshot_identifier"]:
        results["snapshots"] = instance_snapshot_info(client, module)
    if not module.params["db_snapshot_identifier"] and not module.params["db_instance_identifier"]:
        results["cluster_snapshots"] = cluster_snapshot_info(client, module)

    module.exit_json(changed=False, **results)


if __name__ == "__main__":
    main()
