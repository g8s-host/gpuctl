import argparse
import sys
from gpuctl import DEFAULT_NAMESPACE
from gpuctl.cli.job import create_job_command, get_jobs_command, delete_job_command, logs_job_command, describe_job_command, pause_job_command, resume_job_command
from gpuctl.cli.pool import get_pools_command, create_pool_command, delete_pool_command, describe_pool_command
from gpuctl.cli.node import get_nodes_command, get_labels_command, label_node_command, add_node_to_pool_command, remove_node_from_pool_command, describe_node_command


def main():
    parser = argparse.ArgumentParser(description='GPU Control CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # create命令
    create_parser = subparsers.add_parser('create', help='Create a job from YAML')
    create_parser.add_argument('-f', '--file', required=True, action='append', help='YAML file path (can be specified multiple times)')
    create_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE,
                               help='Kubernetes namespace')

    # get命令
    get_parser = subparsers.add_parser('get', help='Get resource information')
    get_subparsers = get_parser.add_subparsers(dest='resource', help='Resource type')

    # get jobs
    jobs_parser = get_subparsers.add_parser('jobs', help='Get jobs')
    jobs_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE,
                             help='Kubernetes namespace')
    jobs_parser.add_argument('--pool', help='Filter by resource pool')
    jobs_parser.add_argument('--type', choices=['training', 'inference', 'notebook', 'compute'],
                             help='Filter by job type')
    # 添加--pods选项，用于查看Pod实例级别信息
    jobs_parser.add_argument(
        "--pods",
        action="store_true",
        help="Show pod-level information instead of deployment/statefulset level"
    )

    # get pools
    pools_parser = get_subparsers.add_parser('pools', help='Get resource pools')

    # get nodes
    nodes_parser = get_subparsers.add_parser('nodes', help='Get nodes')
    nodes_parser.add_argument('--pool', help='Filter by resource pool')
    nodes_parser.add_argument('--gpu-type', help='Filter by GPU type')
    
    # get labels
    labels_parser = get_subparsers.add_parser('labels', help='Get node labels')
    labels_parser.add_argument('node_name', help='Node name')
    labels_parser.add_argument('--key', help='Label key to filter')

    # delete命令
    delete_parser = subparsers.add_parser('delete', help='Delete a resource')
    delete_subparsers = delete_parser.add_subparsers(dest='resource', help='Resource type to delete')
    
    # 支持直接使用delete -f <yaml_file>形式
    delete_parser.add_argument('-f', '--file', help='YAML file path (alternative to specifying resource type)')
    delete_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE,
                              help='Kubernetes namespace')
    delete_parser.add_argument('--force', action='store_true', help='Force delete resource')
    
    # delete job
    job_delete_parser = delete_subparsers.add_parser('job', help='Delete a job')
    job_delete_parser.add_argument('job_name', help='Job name to delete')
    job_delete_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE,
                                  help='Kubernetes namespace')
    job_delete_parser.add_argument('--force', action='store_true', help='Force delete job')
    
    # delete node label (keep existing functionality)

    # logs命令
    logs_parser = subparsers.add_parser('logs', help='Get job logs')
    logs_parser.add_argument('job_name', help='Job name')
    logs_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE,
                             help='Kubernetes namespace')
    logs_parser.add_argument('-f', '--follow', action='store_true',
                             help='Follow log output')

    # label命令
    label_parser = subparsers.add_parser('label', help='Manage node labels')
    label_subparsers = label_parser.add_subparsers(dest='action', help='Label action')
    
    # label node
    node_label_parser = label_subparsers.add_parser('node', help='Manage node labels')
    node_label_parser.add_argument('label', help='Label key=value pair or key for deletion')
    node_label_parser.add_argument('node_name', nargs='+', help='Node name(s)')
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

    # describe command
    describe_parser = subparsers.add_parser('describe', help='Describe resource details')
    describe_subparsers = describe_parser.add_subparsers(dest='resource', help='Resource type')

    # describe job
    job_describe_parser = describe_subparsers.add_parser('job', help='Describe job details')
    job_describe_parser.add_argument('job_id', help='Job ID')
    job_describe_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE, help='Kubernetes namespace')

    # describe pool
    pool_describe_parser = describe_subparsers.add_parser('pool', help='Describe pool details')
    pool_describe_parser.add_argument('pool_name', help='Resource pool name')

    # describe node
    node_describe_parser = describe_subparsers.add_parser('node', help='Describe node details')
    node_describe_parser.add_argument('node_name', help='Node name')

    # pause command
    pause_parser = subparsers.add_parser('pause', help='Pause a running job')
    pause_parser.add_argument('job_name', help='Job name to pause')
    pause_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE, help='Kubernetes namespace')

    # resume command
    resume_parser = subparsers.add_parser('resume', help='Resume a paused job')
    resume_parser.add_argument('job_name', help='Job name to resume')
    resume_parser.add_argument('-n', '--namespace', default=DEFAULT_NAMESPACE, help='Kubernetes namespace')

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
            elif args.resource == 'labels':
                return get_labels_command(args)
            else:
                print(f"Unknown resource type: {args.resource}")
                return 1
        elif args.command == 'delete':
            # 安全检查args.job_name属性
            job_name = getattr(args, 'job_name', None)
            if args.resource == 'job' or job_name:
                # 处理delete job <job_name>命令
                return delete_job_command(args)
            elif args.file:
                # 处理delete -f <yaml_file>命令
                return delete_job_command(args)
            else:
                print("Error: Must specify either -f/--file or resource type (e.g., 'delete job <job_name>')")
                delete_parser.print_help()
                return 1
        elif args.command == 'logs':
            return logs_job_command(args)
        elif args.command == 'pause':
            return pause_job_command(args)
        elif args.command == 'resume':
            return resume_job_command(args)
        elif args.command == 'label' and args.action == 'node':
            return label_node_command(args)
        elif args.command == 'add' and args.resource == 'node':
            return add_node_to_pool_command(args)
        elif args.command == 'remove' and args.resource == 'node':
            return remove_node_from_pool_command(args)
        elif args.command == 'describe':
            if args.resource == 'job':
                return describe_job_command(args)
            elif args.resource == 'pool':
                return describe_pool_command(args)
            elif args.resource == 'node':
                return describe_node_command(args)
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