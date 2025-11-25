import argparse
import sys
from gpuctl.cli.create import create_command
from gpuctl.cli.get import get_jobs_command
from gpuctl.cli.delete import delete_command
from gpuctl.cli.logs import logs_command


def main():
    parser = argparse.ArgumentParser(description='GPU Control CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # create命令
    create_parser = subparsers.add_parser('create', help='Create a job from YAML')
    create_parser.add_argument('-f', '--file', required=True, help='YAML file path')
    create_parser.add_argument('-n', '--namespace', default='default',
                               help='Kubernetes namespace')

    # get命令
    get_parser = subparsers.add_parser('get', help='Get job information')
    get_subparsers = get_parser.add_subparsers(dest='resource', help='Resource type')

    jobs_parser = get_subparsers.add_parser('jobs', help='Get jobs')
    jobs_parser.add_argument('-n', '--namespace', default='default',
                             help='Kubernetes namespace')
    jobs_parser.add_argument('--pool', help='Filter by resource pool')
    jobs_parser.add_argument('--type', choices=['training', 'inference', 'notebook'],
                             help='Filter by job type')

    # delete命令
    delete_parser = subparsers.add_parser('delete', help='Delete a job')
    delete_parser.add_argument('-f', '--file', help='YAML file path')
    delete_parser.add_argument('job_name', nargs='?', help='Job name')

    # logs命令
    logs_parser = subparsers.add_parser('logs', help='Get job logs')
    logs_parser.add_argument('job_name', help='Job name')
    logs_parser.add_argument('-n', '--namespace', default='default',
                             help='Kubernetes namespace')
    logs_parser.add_argument('-f', '--follow', action='store_true',
                             help='Follow log output')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'create':
            return create_command(args)
        elif args.command == 'get' and args.resource == 'jobs':
            return get_jobs_command(args)
        elif args.command == 'delete':
            return delete_command(args)
        elif args.command == 'logs':
            return logs_command(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())