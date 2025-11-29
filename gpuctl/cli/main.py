import argparse
import sys
from gpuctl.cli.job import create_job_command, get_jobs_command, delete_job_command, logs_job_command
from gpuctl.cli.pool import get_pools_command, create_pool_command, delete_pool_command
from gpuctl.cli.node import get_nodes_command, label_node_command, add_node_to_pool_command, remove_node_from_pool_command


def main():
    parser = argparse.ArgumentParser(description='GPU Control CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # create命令
    create_parser = subparsers.add_parser('create', help='Create a job from YAML')
    create_parser.add_argument('-f', '--file', required=True, help='YAML file path')
    create_parser.add_argument('-n', '--namespace', default='default',
                               help='Kubernetes namespace')

    # get命令
    get_parser = subparsers.add_parser('get', help='Get resource information')
    get_subparsers = get_parser.add_subparsers(dest='resource', help='Resource type')

    # get jobs
    jobs_parser = get_subparsers.add_parser('jobs', help='Get jobs')
    jobs_parser.add_argument('-n', '--namespace', default='default',
                             help='Kubernetes namespace')
    jobs_parser.add_argument('--pool', help='Filter by resource pool')
    jobs_parser.add_argument('--type', choices=['training', 'inference', 'notebook'],
                             help='Filter by job type')

    # get pools
    pools_parser = get_subparsers.add_parser('pools', help='Get resource pools')

    # get nodes
    nodes_parser = get_subparsers.add_parser('nodes', help='Get nodes')
    nodes_parser.add_argument('--pool', help='Filter by resource pool')
    nodes_parser.add_argument('--gpu-type', help='Filter by GPU type')

    # delete命令
    delete_parser = subparsers.add_parser('delete', help='Delete a resource')
    delete_parser.add_argument('-f', '--file', help='YAML file path')
    delete_parser.add_argument('resource_name', nargs='?', help='Resource name')
    delete_parser.add_argument('-n', '--namespace', default='default',
                              help='Kubernetes namespace')

    # logs命令
    logs_parser = subparsers.add_parser('logs', help='Get job logs')
    logs_parser.add_argument('job_name', help='Job name')
    logs_parser.add_argument('-n', '--namespace', default='default',
                             help='Kubernetes namespace')
    logs_parser.add_argument('-f', '--follow', action='store_true',
                             help='Follow log output')

    # label命令
    label_parser = subparsers.add_parser('label', help='Manage node labels')
    label_subparsers = label_parser.add_subparsers(dest='action', help='Label action')
    
    # label node
    node_label_parser = label_subparsers.add_parser('node', help='Manage node labels')
    node_label_parser.add_argument('node_name', nargs='+', help='Node name(s)')
    node_label_parser.add_argument('label', nargs='?', help='Label key=value pair')
    node_label_parser.add_argument('--delete', action='store_true', help='Delete label')
    node_label_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing label')

    # add node to pool
    add_parser = subparsers.add_parser('add', help='Add resources to pool')
    add_subparsers = add_parser.add_subparsers(dest='resource', help='Resource type')
    add_node_parser = add_subparsers.add_parser('node', help='Add node to pool')
    add_node_parser.add_argument('node_name', nargs='+', help='Node name(s)')
    add_node_parser.add_argument('--pool', required=True, help='Resource pool name')

    # remove node from pool
    remove_parser = subparsers.add_parser('remove', help='Remove resources from pool')
    remove_subparsers = remove_parser.add_subparsers(dest='resource', help='Resource type')
    remove_node_parser = remove_subparsers.add_parser('node', help='Remove node from pool')
    remove_node_parser.add_argument('node_name', nargs='+', help='Node name(s)')
    remove_node_parser.add_argument('--pool', required=True, help='Resource pool name')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'create':
            return create_job_command(args)
        elif args.command == 'get':
            if args.resource == 'jobs':
                return get_jobs_command(args)
            elif args.resource == 'pools':
                return get_pools_command(args)
            elif args.resource == 'nodes':
                return get_nodes_command(args)
            else:
                print(f"Unknown resource type: {args.resource}")
                return 1
        elif args.command == 'delete':
            return delete_job_command(args)
        elif args.command == 'logs':
            return logs_job_command(args)
        elif args.command == 'label' and args.action == 'node':
            return label_node_command(args)
        elif args.command == 'add' and args.resource == 'node':
            return add_node_to_pool_command(args)
        elif args.command == 'remove' and args.resource == 'node':
            return remove_node_from_pool_command(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())