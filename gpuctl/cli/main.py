import argparse
import sys
from gpuctl import DEFAULT_NAMESPACE
from gpuctl.cli.job import create_job_command, get_jobs_command, delete_job_command, logs_job_command, describe_job_command, apply_job_command
from gpuctl.cli.pool import get_pools_command, create_pool_command, delete_pool_command, describe_pool_command
from gpuctl.cli.node import get_nodes_command, get_labels_command, label_node_command, describe_node_command
from gpuctl.cli.quota import create_quota_command, get_quotas_command, describe_quota_command, delete_quota_command, get_namespaces_command, describe_namespace_command, delete_namespace_command
from gpuctl.client.priority_client import PriorityClient
from gpuctl.parser.base_parser import BaseParser


def main():
    parser = argparse.ArgumentParser(description='GPU Control CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # create command
    create_parser = subparsers.add_parser('create', help='Create a job from YAML')
    create_parser.add_argument('-f', '--file', required=True, nargs='+', help='YAML file path(s)')
    create_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE,
                               help='Kubernetes namespace')
    create_parser.add_argument('--json', action='store_true', help='Output in JSON format')



    # get command
    get_parser = subparsers.add_parser('get', help='Get resource information')
    get_subparsers = get_parser.add_subparsers(dest='resource', help='Resource type')

    # get jobs
    jobs_parser = get_subparsers.add_parser('jobs', help='Get jobs')
    jobs_parser.add_argument('-n', '--namespace', default=None,
                             help='Kubernetes namespace (optional, if not specified, list jobs from all namespaces)')
    jobs_parser.add_argument('--pool', help='Filter by resource pool')
    jobs_parser.add_argument('--kind', choices=['training', 'inference', 'notebook', 'compute'],
                             help='Filter by job kind')
    # Add --pods option to view pod-level information
    jobs_parser.add_argument(
        "--pods",
        action="store_true",
        help="Show pod-level information instead of deployment/statefulset level"
    )
    jobs_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # get pools
    pools_parser = get_subparsers.add_parser('pools', help='Get resource pools')
    pools_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # get nodes
    nodes_parser = get_subparsers.add_parser('nodes', help='Get nodes')
    nodes_parser.add_argument('--pool', help='Filter by resource pool')
    nodes_parser.add_argument('--gpu-type', help='Filter by GPU type')
    nodes_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    # get labels
    labels_parser = get_subparsers.add_parser('labels', help='Get node labels')
    labels_parser.add_argument('node_name', help='Node name')
    labels_parser.add_argument('--key', help='Label key to filter')
    labels_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # get quotas
    quotas_parser = get_subparsers.add_parser('quotas', help='Get resource quotas')
    quotas_parser.add_argument('namespace', nargs='?', help='Filter by namespace name')
    quotas_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    # get namespaces
    ns_parser = get_subparsers.add_parser('ns', help='Get namespaces (alias for namespaces)')
    ns_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    namespaces_parser = get_subparsers.add_parser('namespaces', help='Get namespaces')
    namespaces_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # apply command
    apply_parser = subparsers.add_parser('apply', help='Apply a resource configuration (create or update)')
    apply_parser.add_argument('-f', '--file', required=True, nargs='+', help='YAML file path(s)')
    apply_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE,
                               help='Kubernetes namespace')
    apply_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a resource')
    delete_subparsers = delete_parser.add_subparsers(dest='resource', help='Resource type to delete')
    
    # Support delete -f <yaml_file> format
    delete_parser.add_argument('-f', '--file', nargs='+', help='YAML file path(s) (alternative to specifying resource type)')
    delete_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE,
                              help='Kubernetes namespace')
    delete_parser.add_argument('--force', action='store_true', help='Force delete resource')
    delete_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    # delete job
    job_delete_parser = delete_subparsers.add_parser('job', help='Delete a job')
    job_delete_parser.add_argument('job_name', help='Job name to delete')
    job_delete_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE,
                                  help='Kubernetes namespace')
    job_delete_parser.add_argument('--force', action='store_true', help='Force delete job')
    job_delete_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # delete quota
    quota_delete_parser = delete_subparsers.add_parser('quota', help='Delete a quota')
    quota_delete_parser.add_argument('quota_name', nargs='?', help='Quota name to delete all quotas with this name')
    quota_delete_parser.add_argument('-f', '--file', help='Quota YAML file path to delete all quotas in file')
    quota_delete_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    quota_delete_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    # delete namespace
    ns_delete_parser = delete_subparsers.add_parser('ns', help='Delete a namespace (alias for namespace)')
    ns_delete_parser.add_argument('namespace_name', help='Namespace name to delete')
    ns_delete_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    ns_delete_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    namespace_delete_parser = delete_subparsers.add_parser('namespace', help='Delete a namespace')
    namespace_delete_parser.add_argument('namespace_name', help='Namespace name to delete')
    namespace_delete_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    namespace_delete_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    # delete pool
    pool_delete_parser = delete_subparsers.add_parser('pool', help='Delete a resource pool')
    pool_delete_parser.add_argument('pool_name', help='Resource pool name to delete')
    pool_delete_parser.add_argument('--force', action='store_true', help='Force delete resource pool')
    pool_delete_parser.add_argument('--json', action='store_true', help='Output in JSON format')



    # delete node label (keep existing functionality)

    # logs command
    logs_parser = subparsers.add_parser('logs', help='Get job logs')
    logs_parser.add_argument('job_name', help='Job name')
    logs_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE,
                             help='Kubernetes namespace')
    logs_parser.add_argument('-f', '--follow', action='store_true',
                             help='Follow log output')
    logs_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # label command
    label_parser = subparsers.add_parser('label', help='Manage node labels')
    label_parser.add_argument('node_name', nargs='+', help='Node name(s)')
    label_parser.add_argument('label', help='Label key=value pair or key for deletion (e.g., gpuType=a100-80g)')
    label_parser.add_argument('--delete', action='store_true', help='Delete label')
    label_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing label')
    label_parser.add_argument('--json', action='store_true', help='Output in JSON format')



    # describe command
    describe_parser = subparsers.add_parser('describe', help='Describe resource details')
    describe_subparsers = describe_parser.add_subparsers(dest='resource', help='Resource type')

    # describe job
    job_describe_parser = describe_subparsers.add_parser('job', help='Describe job details')
    job_describe_parser.add_argument('job_id', help='Job ID')
    job_describe_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE, help='Kubernetes namespace')
    job_describe_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # describe pool
    pool_describe_parser = describe_subparsers.add_parser('pool', help='Describe pool details')
    pool_describe_parser.add_argument('pool_name', help='Resource pool name')
    pool_describe_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # describe node
    node_describe_parser = describe_subparsers.add_parser('node', help='Describe node details')
    node_describe_parser.add_argument('node_name', help='Node name')
    node_describe_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # describe quota
    quota_describe_parser = describe_subparsers.add_parser('quota', help='Describe quota details')
    quota_describe_parser.add_argument('namespace_name', help='Namespace name')
    quota_describe_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    # describe namespace
    ns_describe_parser = describe_subparsers.add_parser('ns', help='Describe namespace details (alias for namespace)')
    ns_describe_parser.add_argument('namespace_name', help='Namespace name')
    ns_describe_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    namespace_describe_parser = describe_subparsers.add_parser('namespace', help='Describe namespace details')
    namespace_describe_parser.add_argument('namespace_name', help='Namespace name')
    namespace_describe_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'create':
            return create_job_command(args)
        elif args.command == 'create-quota':
            return create_quota_command(args)
        elif args.command == 'get':
            if args.resource == 'jobs':
                return get_jobs_command(args)
            elif args.resource == 'pools':
                return get_pools_command(args)
            elif args.resource == 'nodes':
                return get_nodes_command(args)
            elif args.resource == 'labels':
                return get_labels_command(args)
            elif args.resource == 'quotas':
                return get_quotas_command(args)
            elif args.resource == 'ns' or args.resource == 'namespaces':
                return get_namespaces_command(args)
            else:
                print(f"Unknown resource type: {args.resource}")
                return 1
        elif args.command == 'apply':
            return apply_job_command(args)
        elif args.command == 'delete':
            if args.file:
                # Handle multiple files
                for file_path in args.file:
                    parsed_obj = BaseParser.parse_yaml_file(file_path)
                    if parsed_obj.kind == "quota":
                        # Pass the current file path to args
                        args.file = [file_path]
                        return delete_quota_command(args)
                    elif parsed_obj.kind == "pool":
                        # For pool deletion from file, we need to extract pool name first
                        import yaml
                        with open(file_path, 'r') as f:
                            pool_config = yaml.safe_load(f)
                        args.pool_name = pool_config.get('pool', {}).get('name') or pool_config.get('name')
                        if not args.pool_name:
                            print("Error: Could not extract pool name from file")
                            return 1
                        return delete_pool_command(args)
                    else:
                        # Pass the current file path to args
                        args.file = [file_path]
                        return delete_job_command(args)
            elif args.resource == 'job':
                return delete_job_command(args)
            elif args.resource == 'quota':
                return delete_quota_command(args)
            elif args.resource == 'ns' or args.resource == 'namespace':
                return delete_namespace_command(args)
            elif args.resource == 'pool':
                return delete_pool_command(args)
            else:
                print("Error: Must specify either -f/--file or resource type (e.g., 'delete job <job_name>')")
                delete_parser.print_help()
                return 1
        elif args.command == 'delete-quota':
            return delete_quota_command(args)
        elif args.command == 'logs':
            return logs_job_command(args)

        elif args.command == 'label':
            return label_node_command(args)

        elif args.command == 'describe':
            if args.resource == 'job':
                return describe_job_command(args)
            elif args.resource == 'pool':
                return describe_pool_command(args)
            elif args.resource == 'node':
                return describe_node_command(args)
            elif args.resource == 'quota':
                return describe_quota_command(args)
            elif args.resource == 'ns' or args.resource == 'namespace':
                return describe_namespace_command(args)
            else:
                print(f"Unknown resource type: {args.resource}")
                return 1
        else:
            print(f"Unknown command: {args.command}")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())