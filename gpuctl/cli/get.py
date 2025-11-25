import argparse
import sys
from gpuctl.client.job_client import JobClient


def get_jobs_command(args):
    """处理get jobs命令"""
    try:
        client = JobClient()

        labels = {}
        if args.pool:
            labels["gpuctl/pool"] = args.pool
        if args.type:
            labels["gpuctl/job-type"] = args.type

        jobs = client.list_jobs(args.namespace, labels)

        if not jobs:
            print("No jobs found")
            return 0

        # 格式化输出
        print(f"{'NAME':<30} {'TYPE':<10} {'POOL':<15} {'STATUS':<10} {'CREATED':<20}")
        print("-" * 90)

        for job in jobs:
            job_type = job["labels"].get("gpuctl/job-type", "unknown")
            pool = job["labels"].get("gpuctl/pool", "default")
            status = "unknown"

            if job["status"]["succeeded"] > 0:
                status = "succeeded"
            elif job["status"]["failed"] > 0:
                status = "failed"
            elif job["status"]["active"] > 0:
                status = "running"
            else:
                status = "pending"

            created = job["creation_timestamp"][:19] if job["creation_timestamp"] else "unknown"

            print(f"{job['name']:<30} {job_type:<10} {pool:<15} {status:<10} {created:<20}")

        return 0

    except Exception as e:
        print(f"❌ Error getting jobs: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description='Get GPU jobs')
    parser.add_argument('-n', '--namespace', default='default', help='Kubernetes namespace')
    parser.add_argument('--pool', help='Filter by resource pool')
    parser.add_argument('--type', choices=['training', 'inference', 'notebook'],
                        help='Filter by job type')

    args = parser.parse_args()
    sys.exit(get_jobs_command(args))