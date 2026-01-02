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
                    "namespace": {}
                }

                if parsed_obj.default:
                    quota_config["default"] = {
                        "cpu": parsed_obj.default.get_cpu_str(),
                        "memory": parsed_obj.default.memory,
                        "gpu": parsed_obj.default.get_gpu_str()
                    }

                for namespace_name, namespace_quota in parsed_obj.namespace.items():
                    quota_config["namespace"][namespace_name] = {
                        "cpu": namespace_quota.get_cpu_str(),
                        "memory": namespace_quota.memory,
                        "gpu": namespace_quota.get_gpu_str()
                    }

                results = client.create_quota_config(quota_config)

                for result in results:
                    print(f"✅ Successfully created quota for namespace: {result['namespace']}")
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


def apply_quota_command(args):
    """Apply resource quota command (create or update)"""
    try:
        client = QuotaClient()

        if not args.file:
            print("❌ Must provide YAML file path (-f/--file)")
            return 1

        file_list = args.file if isinstance(args.file, list) else [args.file]

        for file_path in file_list:
            print(f"\n📝 Applying file: {file_path}")

            try:
                parsed_obj = BaseParser.parse_yaml_file(file_path)

                if parsed_obj.kind != "quota":
                    print(f"❌ Unsupported kind: {parsed_obj.kind}")
                    continue

                quota_name = parsed_obj.metadata.name
                namespaces = parsed_obj.namespace or {}
                default_quota = parsed_obj.default

                applied_count = 0
                updated_count = 0

                if default_quota:
                    result = client.apply_default_quota(
                        quota_name=quota_name,
                        cpu=str(default_quota.get_cpu_str()) if default_quota.get_cpu_str() else None,
                        memory=default_quota.memory,
                        gpu=str(default_quota.get_gpu_str()) if default_quota.get_gpu_str() else None
                    )
                    if result['status'] == 'created':
                        applied_count += 1
                        print(f"✅ Created default quota in namespace 'default'")
                    elif result['status'] == 'updated':
                        updated_count += 1
                        print(f"🔄 Updated default quota in namespace 'default'")
                    print(f"   CPU: {result['cpu']}, Memory: {result['memory']}, GPU: {result['gpu']}")

                for namespace_name, namespace_quota in namespaces.items():
                    if namespace_name == "default":
                        continue
                    result = client.apply_quota(
                        quota_name=quota_name,
                        namespace_name=namespace_name,
                        cpu=namespace_quota.get_cpu_str() if namespace_quota.get_cpu_str() else None,
                        memory=namespace_quota.memory,
                        gpu=namespace_quota.get_gpu_str() if namespace_quota.get_gpu_str() else None
                    )
                    if result['status'] == 'created':
                        applied_count += 1
                        print(f"✅ Created quota for namespace: {namespace_name}")
                    elif result['status'] == 'updated':
                        updated_count += 1
                        print(f"🔄 Updated quota for namespace: {namespace_name}")
                    print(f"   Namespace: {result['namespace']}, CPU: {result['cpu']}, Memory: {result['memory']}, GPU: {result['gpu']}")

                print(f"\n📊 Summary: {applied_count} created, {updated_count} updated")

            except ParserError as e:
                print(f"❌ Parser error: {e}")
            except Exception as e:
                print(f"❌ Error applying file {file_path}: {e}")

        return 0
    except Exception as e:
        print(f"❌ Error applying quota: {e}")
        return 1


def get_quotas_command(args):
    """Get resource quotas list command"""
    try:
        client = QuotaClient()

        if args.namespace:
            quota = client.get_quota(args.namespace)
            if quota:
                print(f"QUOTA NAME: {quota['name']}")
                print(f"NAMESPACE: {quota['namespace']}")
                print(f"CPU: {quota['hard'].get('cpu', 'N/A')}")
                print(f"MEMORY: {quota['hard'].get('memory', 'N/A')}")
                print(f"GPU: {quota['hard'].get('nvidia.com/gpu', quota['hard'].get('gpu', 'N/A'))}")
                print(f"STATUS: {quota['status']}")
            else:
                print(f"❌ Quota not found for namespace: {args.namespace}")
                return 1
        else:
            quotas = client.list_quotas()
            
            # Calculate column widths dynamically
            headers = ['QUOTA NAME', 'NAMESPACE', 'CPU', 'MEMORY', 'GPU', 'STATUS']
            col_widths = {'name': 15, 'namespace': 15, 'cpu': 10, 'memory': 12, 'gpu': 8, 'status': 10}
            
            quota_rows = []
            for quota in quotas:
                gpu_value = quota['hard'].get('nvidia.com/gpu', quota['hard'].get('gpu', 'N/A'))
                quota_rows.append({
                    'name': quota['name'],
                    'namespace': quota['namespace'],
                    'cpu': str(quota['hard'].get('cpu', 'N/A')),
                    'memory': str(quota['hard'].get('memory', 'N/A')),
                    'gpu': str(gpu_value),
                    'status': quota['status']
                })
                
                col_widths['name'] = max(col_widths['name'], len(quota['name']))
                col_widths['namespace'] = max(col_widths['namespace'], len(quota['namespace']))
                col_widths['cpu'] = max(col_widths['cpu'], len(str(quota['hard'].get('cpu', 'N/A'))))
                col_widths['memory'] = max(col_widths['memory'], len(str(quota['hard'].get('memory', 'N/A'))))
                col_widths['gpu'] = max(col_widths['gpu'], len(str(gpu_value)))
                col_widths['status'] = max(col_widths['status'], len(quota['status']))
            
            print(f"{headers[0]:<{col_widths['name']}}  {headers[1]:<{col_widths['namespace']}}  {headers[2]:<{col_widths['cpu']}}  {headers[3]:<{col_widths['memory']}}  {headers[4]:<{col_widths['gpu']}}  {headers[5]:<{col_widths['status']}}")
            
            for row in quota_rows:
                print(f"{row['name']:<{col_widths['name']}}  {row['namespace']:<{col_widths['namespace']}}  {row['cpu']:<{col_widths['cpu']}}  {row['memory']:<{col_widths['memory']}}  {row['gpu']:<{col_widths['gpu']}}  {row['status']:<{col_widths['status']}}")

        return 0
    except Exception as e:
        print(f"❌ Error getting quotas: {e}")
        return 1


def describe_quota_command(args):
    """Describe resource quota details command"""
    try:
        client = QuotaClient()

        quota = client.describe_quota(args.namespace_name)
        if not quota:
            print(f"❌ Quota not found for namespace: {args.namespace_name}")
            return 1

        print(f"📋 Quota Details: {args.namespace_name}")
        print(f"📊 Name: {quota.get('name', 'N/A')}")
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
                namespaces_to_delete = list(parsed_obj.namespace.keys())

                namespaces_to_delete_result = []
                for ns in namespaces_to_delete:
                    namespaces_to_delete_result.append(ns)

                if parsed_obj.default:
                    namespaces_to_delete_result.append("default")

                unique_namespaces = list(set(namespaces_to_delete_result))

                print(f"⚠️  Warning: About to delete {len(unique_namespaces)} namespaces and all resources within:")
                for ns in unique_namespaces:
                    print(f"   - {ns}")

                if not args.force:
                    confirm = input("\nAre you sure you want to continue? (Y/n): ").strip().upper()
                    if confirm != 'Y':
                        print("❌ Cancelled.")
                        return 0

                result = client.delete_quota_config(quota_name, include_default=bool(parsed_obj.default))

                print(f"✅ Deleted quotas for config: {quota_name}")
                for deleted in result.get('deleted', []):
                    print(f"   - Namespace: {deleted['namespace']}")

                if result.get('failed'):
                    print(f"❌ Failed to delete:")
                    for failed in result['failed']:
                        print(f"   - Namespace: {failed['namespace']}, Error: {failed['error']}")

            except ParserError as e:
                print(f"❌ Parser error: {e}")
                return 1
        elif args.namespace_name:
            print(f"⚠️  Warning: About to delete namespace '{args.namespace_name}' and all resources within")

            if not args.force:
                confirm = input("\nAre you sure you want to continue? (Y/n): ").strip().upper()
                if confirm != 'Y':
                    print("❌ Cancelled.")
                    return 0

            success = client.delete_quota(args.namespace_name)
            if success:
                print(f"✅ Successfully deleted quota for namespace: {args.namespace_name}")
            else:
                print(f"❌ Quota not found for namespace: {args.namespace_name}")
                return 1
        else:
            print("❌ Must provide YAML file path (-f/--file) or namespace name")
            return 1

        return 0
    except Exception as e:
        print(f"❌ Error deleting quota: {e}")
        return 1
