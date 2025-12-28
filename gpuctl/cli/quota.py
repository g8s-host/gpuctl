from gpuctl.parser.base_parser import BaseParser, ParserError
from gpuctl.client.quota_client import QuotaClient


def create_quota_command(args):
    """Create resource quota command"""
    try:
        client = QuotaClient()

        file_list = args.file if isinstance(args.file, list) else [args.file]

        for file_path in file_list:
            print(f"\n📝 Processing file: {file_path}")

            try:
                parsed_obj = BaseParser.parse_yaml_file(file_path)

                if parsed_obj.kind != "quota":
                    print(f"❌ Unsupported kind: {parsed_obj.kind}")
                    continue

                quota_config = {
                    "name": parsed_obj.metadata.name,
                    "description": parsed_obj.metadata.description,
                    "users": {}
                }

                if parsed_obj.default:
                    quota_config["default"] = {
                        "cpu": parsed_obj.default.get_cpu_str(),
                        "memory": parsed_obj.default.memory,
                        "gpu": parsed_obj.default.get_gpu_str()
                    }

                for user_name, user_quota in parsed_obj.users.items():
                    quota_config["users"][user_name] = {
                        "cpu": user_quota.get_cpu_str(),
                        "memory": user_quota.memory,
                        "gpu": user_quota.get_gpu_str()
                    }

                results = client.create_quota_config(quota_config)

                for result in results:
                    print(f"✅ Successfully created quota for user: {result['user']}")
                    print(f"   Namespace: {result['namespace']}")
                    print(f"   CPU: {result['cpu']}")
                    print(f"   Memory: {result['memory']}")
                    print(f"   GPU: {result['gpu']}")

            except ParserError as e:
                print(f"❌ Parser error: {e}")
            except Exception as e:
                print(f"❌ Error processing file {file_path}: {e}")

        return 0
    except Exception as e:
        print(f"❌ Error creating quota: {e}")
        return 1


def get_quotas_command(args):
    """Get resource quotas list command"""
    try:
        client = QuotaClient()

        if args.user:
            quota = client.get_quota(args.user)
            if quota:
                print(f"{'QUOTA NAME':<20} {'USER':<15} {'CPU':<10} {'MEMORY':<12} {'GPU':<8} {'STATUS':<10}")
                print(f"{quota['name']:<20} {quota['user']:<15} {quota['hard'].get('cpu', 'N/A'):<10} {quota['hard'].get('memory', 'N/A'):<12} {quota['hard'].get('gpu', 'N/A'):<8} {quota['status']:<10}")
            else:
                print(f"❌ Quota not found for user: {args.user}")
                return 1
        else:
            quotas = client.list_quotas()
            print(f"{'QUOTA NAME':<20} {'USER':<15} {'CPU':<10} {'MEMORY':<12} {'GPU':<8} {'STATUS':<10}")

            for quota in quotas:
                gpu_value = quota['hard'].get('nvidia.com/gpu', quota['hard'].get('gpu', 'N/A'))
                print(f"{quota['name']:<20} {quota['user']:<15} {quota['hard'].get('cpu', 'N/A'):<10} {quota['hard'].get('memory', 'N/A'):<12} {gpu_value:<8} {quota['status']:<10}")

        return 0
    except Exception as e:
        print(f"❌ Error getting quotas: {e}")
        return 1


def describe_quota_command(args):
    """Describe resource quota details command"""
    try:
        client = QuotaClient()

        quota = client.describe_quota(args.user_name)
        if not quota:
            print(f"❌ Quota not found for user: {args.user_name}")
            return 1

        print(f"📋 Quota Details: {args.user_name}")
        print(f"📊 Name: {quota.get('name', 'N/A')}")
        print(f"👤 User: {quota.get('user', 'N/A')}")
        print(f"📦 Namespace: {quota.get('namespace', 'N/A')}")
        print(f"📈 Status: {quota.get('status', 'N/A')}")

        print(f"\n💻 Resource Limits:")
        hard = quota.get('hard', {})
        used = quota.get('used', {})

        cpu_hard = hard.get('cpu', 'unlimited')
        cpu_used = used.get('cpu', '0')
        print(f"   CPU:     {cpu_used}/{cpu_hard}")

        mem_hard = hard.get('memory', 'unlimited')
        mem_used = used.get('memory', '0')
        print(f"   Memory:  {mem_used}/{mem_hard}")

        gpu_hard = hard.get('nvidia.com/gpu', 'unlimited')
        gpu_used = used.get('nvidia.com/gpu', '0')
        print(f"   GPU:     {gpu_used}/{gpu_hard}")

        return 0
    except Exception as e:
        print(f"❌ Error describing quota: {e}")
        return 1


def delete_quota_command(args):
    """Delete resource quota command"""
    try:
        client = QuotaClient()

        if args.file:
            try:
                parsed_obj = BaseParser.parse_yaml_file(args.file)

                if parsed_obj.kind != "quota":
                    print(f"❌ Unsupported kind: {parsed_obj.kind}")
                    return 1

                quota_name = parsed_obj.metadata.name
                users_to_delete = list(parsed_obj.users.keys())

                print(f"⚠️  Warning: About to delete {len(users_to_delete)} namespaces and all resources within:")
                for user in users_to_delete:
                    print(f"   - {user}")

                if not args.force:
                    confirm = input("\nAre you sure you want to continue? (Y/n): ").strip().upper()
                    if confirm != 'Y':
                        print("❌ Cancelled.")
                        return 0

                result = client.delete_quota_config(quota_name)

                print(f"✅ Deleted quotas for config: {quota_name}")
                for deleted in result.get('deleted', []):
                    print(f"   - User: {deleted['user']}, Namespace: {deleted['namespace']}")

                if result.get('failed'):
                    print(f"❌ Failed to delete:")
                    for failed in result['failed']:
                        print(f"   - User: {failed['user']}, Error: {failed['error']}")

            except ParserError as e:
                print(f"❌ Parser error: {e}")
                return 1
        elif args.user_name:
            print(f"⚠️  Warning: About to delete namespace '{args.user_name}' and all resources within")

            if not args.force:
                confirm = input("\nAre you sure you want to continue? (Y/n): ").strip().upper()
                if confirm != 'Y':
                    print("❌ Cancelled.")
                    return 0

            success = client.delete_quota(args.user_name)
            if success:
                print(f"✅ Successfully deleted quota for user: {args.user_name}")
            else:
                print(f"❌ Quota not found for user: {args.user_name}")
                return 1
        else:
            print("❌ Must provide YAML file path (-f/--file) or user name")
            return 1

        return 0
    except Exception as e:
        print(f"❌ Error deleting quota: {e}")
        return 1
