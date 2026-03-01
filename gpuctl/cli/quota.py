from gpuctl.parser.base_parser import BaseParser, ParserError
from gpuctl.client.quota_client import QuotaClient
from gpuctl.constants import Labels, NS_LABEL_SELECTOR


def create_quota_command(args):
    """Create resource quota command"""
    try:
        client = QuotaClient()

        file_list = args.file if isinstance(args.file, list) else [args.file]
        all_results = []

        for file_path in file_list:
            if not args.json:
                print(f"\n📝 Processing file: {file_path}")

            try:
                parsed_obj = BaseParser.parse_yaml_file(file_path)

                if parsed_obj.kind != "quota":
                    error = {"error": f"Unsupported kind: {parsed_obj.kind}", "file": file_path}
                    if args.json:
                        all_results.append(error)
                    else:
                        print(f"❌ Unsupported kind: {parsed_obj.kind}")
                    continue

                quota_config = {
                    "name": parsed_obj.quota.name,
                    "description": parsed_obj.quota.description,
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
                all_results.extend(results)

                for result in results:
                    if not args.json:
                        print(f"✅ Successfully created quota for namespace: {result['namespace']}")
                        print(f"   Namespace: {result['namespace']}")
                        print(f"   CPU: {result['cpu']}")
                        print(f"   Memory: {result['memory']}")
                        print(f"   GPU: {result['gpu']}")

            except ParserError as e:
                error = {"error": f"Parser error: {str(e)}", "file": file_path}
                if args.json:
                    all_results.append(error)
                else:
                    print(f"❌ Parser error: {e}")
            except Exception as e:
                error = {"error": f"Error processing file {file_path}: {str(e)}", "file": file_path}
                if args.json:
                    all_results.append(error)
                else:
                    print(f"❌ Error processing file {file_path}: {e}")

        if args.json:
            import json
            print(json.dumps(all_results, indent=2))

        return 0
    except Exception as e:
        if args.json:
            import json
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"❌ Error creating quota: {e}")
        return 1


def apply_quota_command(args):
    """Apply resource quota command (create or update)"""
    try:
        client = QuotaClient()

        if not args.file:
            error = {"error": "Must provide YAML file path (-f/--file)"}
            if args.json:
                import json
                print(json.dumps(error, indent=2))
            else:
                print("❌ Must provide YAML file path (-f/--file)")
            return 1

        file_list = args.file if isinstance(args.file, list) else [args.file]
        all_results = []

        for file_path in file_list:
            if not args.json:
                print(f"\n📝 Applying file: {file_path}")

            try:
                parsed_obj = BaseParser.parse_yaml_file(file_path)

                if parsed_obj.kind != "quota":
                    error = {"error": f"Unsupported kind: {parsed_obj.kind}", "file": file_path}
                    if args.json:
                        all_results.append(error)
                    else:
                        print(f"❌ Unsupported kind: {parsed_obj.kind}")
                    continue

                quota_name = parsed_obj.quota.name
                namespaces = parsed_obj.namespace or {}
                default_quota = parsed_obj.default

                file_results = {
                    "file": file_path,
                    "quota_name": quota_name,
                    "results": [],
                    "summary": {
                        "created": 0,
                        "updated": 0
                    }
                }

                if default_quota:
                    result = client.apply_default_quota(
                        quota_name=quota_name,
                        cpu=str(default_quota.get_cpu_str()) if default_quota.get_cpu_str() else None,
                        memory=default_quota.memory,
                        gpu=str(default_quota.get_gpu_str()) if default_quota.get_gpu_str() else None
                    )
                    file_results["results"].append(result)
                    if result['status'] == 'created':
                        file_results["summary"]["created"] += 1
                        if not args.json:
                            print(f"✅ Created default quota in namespace 'default'")
                    elif result['status'] == 'updated':
                        file_results["summary"]["updated"] += 1
                        if not args.json:
                            print(f"🔄 Updated default quota in namespace 'default'")
                    if not args.json:
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
                    file_results["results"].append(result)
                    if result['status'] == 'created':
                        file_results["summary"]["created"] += 1
                        if not args.json:
                            print(f"✅ Created quota for namespace: {namespace_name}")
                    elif result['status'] == 'updated':
                        file_results["summary"]["updated"] += 1
                        if not args.json:
                            print(f"🔄 Updated quota for namespace: {namespace_name}")
                    if not args.json:
                        print(f"   Namespace: {result['namespace']}, CPU: {result['cpu']}, Memory: {result['memory']}, GPU: {result['gpu']}")

                all_results.append(file_results)
                if not args.json:
                    print(f"\n📊 Summary: {file_results['summary']['created']} created, {file_results['summary']['updated']} updated")

            except ParserError as e:
                error = {"error": f"Parser error: {str(e)}", "file": file_path}
                all_results.append(error)
                if not args.json:
                    print(f"❌ Parser error: {e}")
            except Exception as e:
                error = {"error": f"Error applying file {file_path}: {str(e)}", "file": file_path}
                all_results.append(error)
                if not args.json:
                    print(f"❌ Error applying file {file_path}: {e}")

        if args.json:
            import json
            print(json.dumps(all_results, indent=2))

        return 0
    except Exception as e:
        if args.json:
            import json
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"❌ Error applying quota: {e}")
        return 1


def get_quotas_command(args):
    """Get resource quotas list command"""
    try:
        client = QuotaClient()
        import json

        if args.namespace:
            quota = client.get_quota(args.namespace)
            if quota:
                if args.json:
                    print(json.dumps(quota, indent=2))
                else:
                    print(f"QUOTA NAME: {quota['name']}")
                    print(f"NAMESPACE: {quota['namespace']}")
                    print(f"CPU: {quota['hard'].get('cpu', 'N/A')}")
                    print(f"MEMORY: {quota['hard'].get('memory', 'N/A')}")
                    print(f"GPU: {quota['hard'].get('nvidia.com/gpu', quota['hard'].get('gpu', 'N/A'))}")
                    print(f"STATUS: {quota['status']}")
            else:
                error = {"error": f"Quota not found for namespace: {args.namespace}"}
                if args.json:
                    print(json.dumps(error, indent=2))
                else:
                    print(f"❌ Quota not found for namespace: {args.namespace}")
                return 1
        else:
            quotas = client.list_quotas()
            
            if args.json:
                print(json.dumps(quotas, indent=2))
            else:
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
        if args.json:
            import json
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"❌ Error getting quotas: {e}")
        return 1


def describe_quota_command(args):
    """Describe resource quota details command"""
    try:
        client = QuotaClient()

        quota = client.describe_quota(args.namespace_name)
        if not quota:
            error = {"error": f"Quota not found for namespace: {args.namespace_name}"}
            if args.json:
                import json
                print(json.dumps(error, indent=2))
            else:
                print(f"❌ Quota not found for namespace: {args.namespace_name}")
            return 1

        if args.json:
            import json
            print(json.dumps(quota, indent=2))
        else:
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
        if args.json:
            import json
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"❌ Error describing quota: {e}")
        return 1


def delete_quota_command(args):
    """Delete resource quota command"""
    try:
        client = QuotaClient()
        import json

        if args.file:
            all_results = []
            for file_path in args.file:
                try:
                    parsed_obj = BaseParser.parse_yaml_file(file_path)

                    if parsed_obj.kind != "quota":
                        error = {"error": f"Unsupported kind: {parsed_obj.kind}"}
                        all_results.append({"file": file_path, "error": error})
                        if args.json:
                            import json
                            print(json.dumps(error, indent=2))
                        else:
                            print(f"❌ Unsupported kind: {parsed_obj.kind}")
                        continue

                    quota_name = parsed_obj.quota.name
                    namespaces_to_delete = list(parsed_obj.namespace.keys())

                    namespaces_to_delete_result = []
                    for ns in namespaces_to_delete:
                        namespaces_to_delete_result.append(ns)

                    if parsed_obj.default:
                        namespaces_to_delete_result.append("default")

                    unique_namespaces = list(set(namespaces_to_delete_result))

                    if not args.force and not args.json:
                        print(f"⚠️  Warning: About to delete {len(unique_namespaces)} namespaces and all resources within:")
                        for ns in unique_namespaces:
                            print(f"   - {ns}")

                        confirm = input("\nAre you sure you want to continue? (Y/n): ").strip().upper()
                        if confirm != 'Y':
                            result = {"status": "cancelled", "message": "Operation cancelled by user"}
                            if args.json:
                                import json
                                print(json.dumps(result, indent=2))
                            else:
                                print("❌ Cancelled.")
                            return 0

                    result = client.delete_quota_config(quota_name, include_default=bool(parsed_obj.default))
                    all_results.append({"file": file_path, "result": result})

                    if args.json:
                        import json
                        print(json.dumps(result, indent=2))
                    else:
                        print(f"✅ Deleted quotas for config: {quota_name}")
                        for deleted in result.get('deleted', []):
                            print(f"   - Namespace: {deleted['namespace']}")

                        if result.get('failed'):
                            print(f"❌ Failed to delete:")
                            for failed in result['failed']:
                                print(f"   - Namespace: {failed['namespace']}, Error: {failed['error']}")
                except ParserError as e:
                    error = {"error": f"Parser error: {str(e)}"}
                    all_results.append({"file": file_path, "error": error})
                    if args.json:
                        import json
                        print(json.dumps(error, indent=2))
                    else:
                        print(f"❌ Parser error: {e}")
                    continue
        elif args.quota_name:
            if not args.force and not args.json:
                print(f"⚠️  Warning: About to delete all quotas with name: '{args.quota_name}'")
                confirm = input("\nAre you sure you want to continue? (Y/n): ").strip().upper()
                if confirm != 'Y':
                    result = {"status": "cancelled", "message": "Operation cancelled by user"}
                    if args.json:
                        print(json.dumps(result, indent=2))
                    else:
                        print("❌ Cancelled.")
                    return 0

            result = client.delete_quota_config(args.quota_name)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"✅ Deleted quotas for config: {args.quota_name}")
                for deleted in result.get('deleted', []):
                    print(f"   - Namespace: {deleted['namespace']}")

                if result.get('failed'):
                    print(f"❌ Failed to delete:")
                    for failed in result['failed']:
                        print(f"   - Namespace: {failed['namespace']}, Error: {failed['error']}")
        else:
            result = {"error": "Must provide YAML file path (-f/--file) or quota name"}
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("❌ Must provide YAML file path (-f/--file) or quota name")
            return 1

        return 0
    except Exception as e:
        error = {"error": str(e)}
        if args.json:
            import json
            print(json.dumps(error, indent=2))
        else:
            print(f"❌ Error deleting quota: {e}")
        return 1


def get_namespaces_command(args):
    """Get namespaces command"""
    try:
        client = QuotaClient()
        
        # Get all namespaces created by this CLI (with g8s.host/namespace label)
        namespaces = client.core_v1.list_namespace(
            label_selector=NS_LABEL_SELECTOR
        )
        
        # Process namespace data
        processed_namespaces = []
        for ns in namespaces.items:
            name = ns.metadata.name
            status = ns.status.phase
            age = ns.metadata.creation_timestamp
            
            processed_namespaces.append({
                "name": name,
                "status": status,
                "age": age
            })
        
        # Add default namespace if not already in the list
        try:
            default_ns = client.core_v1.read_namespace("default")
            # Check if default namespace is already in the list
            default_exists = any(ns["name"] == "default" for ns in processed_namespaces)
            if not default_exists:
                processed_namespaces.append({
                    "name": default_ns.metadata.name,
                    "status": default_ns.status.phase,
                    "age": default_ns.metadata.creation_timestamp
                })
        except Exception as e:
            # Ignore error if default namespace cannot be read
            pass
        
        # Output in JSON format if requested
        if args.json:
            import json
            print(json.dumps(processed_namespaces, default=str, indent=2))
        else:
            # Print table format similar to kubectl get ns
            headers = ["NAME", "STATUS", "AGE"]
            print(f"{headers[0]:<30} {headers[1]:<10} {headers[2]:<20}")
            for ns in processed_namespaces:
                print(f"{ns['name']:<30} {ns['status']:<10} {str(ns['age']):<20}")
        
        return 0
    except Exception as e:
        error = {"error": str(e)}
        if args.json:
            import json
            print(json.dumps(error, indent=2))
        else:
            print(f"❌ Error getting namespaces: {e}")
        return 1


def describe_namespace_command(args):
    """Describe namespace command"""
    try:
        client = QuotaClient()
        
        # Get namespace details
        namespace = client.core_v1.read_namespace(args.namespace_name)
        
        # Verify it's a namespace created by this CLI
        labels = namespace.metadata.labels or {}
        if not labels.get(Labels.NS_MARKER) == "true":
            raise ValueError(f"Namespace {args.namespace_name} was not created by this CLI")
        
        # Get quota information for this namespace
        quota = client.get_quota(args.namespace_name)
        
        # Output in JSON format if requested
        if args.json:
            import json
            result = {
                "name": namespace.metadata.name,
                "status": namespace.status.phase,
                "age": namespace.metadata.creation_timestamp,
                "labels": labels,
                "quota": quota
            }
            print(json.dumps(result, default=str, indent=2))
        else:
            # Print detailed information
            print(f"📋 Namespace Details: {namespace.metadata.name}")
            print(f"📊 Name: {namespace.metadata.name}")
            print(f"📈 Status: {namespace.status.phase}")
            print(f"⏰ Age: {str(namespace.metadata.creation_timestamp)}")
            print(f"🏷️  Labels: {labels}")
            
            if quota:
                hard = quota.get('hard', {})
                used = quota.get('used', {})
                print("\n💾 Resource Quota:")
                print(f"   Name: {quota.get('name', 'N/A')}")
                print(f"   CPU: {hard.get('cpu', 'N/A')}")
                print(f"   Memory: {hard.get('memory', 'N/A')}")
                print(f"   GPU: {hard.get('nvidia.com/gpu', 'N/A')}")
                
                if used:
                    print("\n📊 Quota Usage:")
                    print(f"   CPU: {used.get('cpu', '0')}/{hard.get('cpu', 'N/A')}")
                    print(f"   Memory: {used.get('memory', '0')}/{hard.get('memory', 'N/A')}")
                    print(f"   GPU: {used.get('nvidia.com/gpu', '0')}/{hard.get('nvidia.com/gpu', 'N/A')}")
        
        return 0
    except Exception as e:
        error = {"error": str(e)}
        if args.json:
            import json
            print(json.dumps(error, indent=2))
        else:
            print(f"❌ Error describing namespace: {e}")
        return 1


def delete_namespace_command(args):
    """Delete namespace command"""
    try:
        client = QuotaClient()
        
        # Verify namespace exists and was created by this CLI
        namespace = client.core_v1.read_namespace(args.namespace_name)
        labels = namespace.metadata.labels or {}
        
        if not labels.get(Labels.NS_MARKER) == "true":
            raise ValueError(f"Namespace {args.namespace_name} was not created by this CLI")
        
        # Confirm deletion if not forced
        if not args.force and not args.json:
            confirm = input(f"⚠️  Warning: About to delete namespace '{args.namespace_name}' and all resources within. Are you sure you want to continue? (Y/n): ").strip().upper()
            if confirm != 'Y':
                print("❌ Cancelled.")
                return 0
        
        # Delete the namespace
        client.core_v1.delete_namespace(args.namespace_name)
        
        # Output result
        if args.json:
            import json
            result = {
                "status": "success",
                "message": f"Successfully deleted namespace: {args.namespace_name}"
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"✅ Successfully deleted namespace: {args.namespace_name}")
        
        return 0
    except Exception as e:
        error = {"error": str(e)}
        if args.json:
            import json
            print(json.dumps(error, indent=2))
        else:
            print(f"❌ Error deleting namespace: {e}")
        return 1
