import sys
from gpuctl.parser.base_parser import BaseParser, ParserError
from gpuctl.kind.training_kind import TrainingKind
from gpuctl.kind.inference_kind import InferenceKind
from gpuctl.kind.notebook_kind import NotebookKind
from gpuctl.client.job_client import JobClient
from gpuctl.client.log_client import LogClient


def _get_detailed_status(waiting_reason: str, waiting_message: str) -> str:
    """Get detailed status from container waiting reason"""
    status_mapping = {
        "ImagePullBackOff": "ImagePullBackOff",
        "ErrImagePull": "ErrImagePull",
        "CrashLoopBackOff": "CrashLoopBackOff",
        "CreateContainerConfigError": "CreateContainerConfigError",
        "CreateContainerError": "CreateContainerError",
        "InvalidImageName": "InvalidImageName",
        "ImageInspectError": "ImageInspectError",
        "RegistryUnavailable": "RegistryUnavailable",
        "RunInitContainerError": "RunInitContainerError",
        "Resizing": "Resizing",
        "Restarting": "Restarting",
        "Waiting": "Waiting",
        "Terminating": "Terminating",
        "Unknown": "Unknown",
    }
    
    if waiting_reason in status_mapping:
        return status_mapping[waiting_reason]
    
    if "BackOff" in waiting_reason:
        return "BackOff"
    
    if "NotFound" in waiting_reason or "not found" in waiting_message.lower():
        return "NotFound"
    
    if "Permission" in waiting_reason or "denied" in waiting_message.lower():
        return "PermissionDenied"
    
    if "Storage" in waiting_reason or "storage" in waiting_message.lower():
        return "StorageError"
    
    return waiting_reason if waiting_reason else "Waiting"


def _format_event_age(timestamp_str: str) -> str:
    """Format event timestamp to age string"""
    if not timestamp_str:
        return "-"
    
    from datetime import datetime, timezone
    
    try:
        event_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - event_time
        
        seconds = delta.total_seconds()
        if seconds < 0:
            seconds = 0
        
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m"
        elif seconds < 86400:
            return f"{int(seconds/3600)}h"
        else:
            return f"{int(seconds/86400)}d"
    except Exception:
        return "-"


# Helper function: handle g8s-host prefix

def remove_prefix(name):
    """Return the original name without any prefix"""
    return name

def add_prefix(name, job_type):
    """Return the original name without adding any prefix"""
    return name


def create_job_command(args):
    """Create job command"""
    try:
        import json
        all_results = []
        
        # 自动初始化优先级类，确保所有所需的PriorityClass存在
        from gpuctl.client.priority_client import PriorityClient
        priority_client = PriorityClient()
        
        if not args.json:
            print("🔍 Checking and initializing priority classes...")
        priority_client.ensure_priority_classes()
        
        # Handle multiple files
        for file_path in args.file:
            if not args.json:
                print(f"\n📝 Processing file: {file_path}")
            
            # Parse YAML file
            parsed_obj = BaseParser.parse_yaml_file(file_path)
            file_result = {
                "file": file_path,
                "kind": parsed_obj.kind,
                "results": []
            }

            # Determine the final namespace: use YAML-specified first, then CLI arg, then default
            # 1. Check if namespace is specified in YAML (job.metadata.namespace)
            yaml_namespace = getattr(parsed_obj, 'job', None) and getattr(parsed_obj.job, 'namespace', None)
            # 2. Use CLI-specified namespace if no YAML namespace
            final_namespace = yaml_namespace or args.namespace
            
            # Check if namespace has quota configured (except for quota and pool/resource kinds)
            if parsed_obj.kind not in ["quota", "pool", "resource"]:
                from gpuctl.client.quota_client import QuotaClient
                quota_client = QuotaClient()
                if not quota_client.namespace_has_quota(final_namespace):
                    error = {"error": f"Namespace '{final_namespace}' does not have quota configured. Please create quota for this namespace first."}
                    file_result["results"].append(error)
                    if args.json:
                        import json
                        print(json.dumps(error, indent=2))
                    else:
                        print(f"❌ Namespace '{final_namespace}' does not have quota configured. Please create quota for this namespace first.")
                    return 1
            
            # Create appropriate handler based on type
            if parsed_obj.kind == "training":
                handler = TrainingKind()
                result = handler.create_training_job(parsed_obj, final_namespace)
                # Display job_id with prefix removed
                display_job_id = remove_prefix(result['job_id'])
                file_result["results"].append(result)
                if not args.json:
                    print(f"✅ Successfully created {parsed_obj.kind} job: {display_job_id}")
                    print(f"📊 Name: {result['name']}")
                    print(f"📦 Namespace: {result['namespace']}")
                    if 'resources' in result:
                        print(f"🖥️  Resources: {result['resources']}")
            elif parsed_obj.kind == "inference":
                handler = InferenceKind()
                result = handler.create_inference_service(parsed_obj, final_namespace)
                # Display job_id with prefix removed
                display_job_id = remove_prefix(result['job_id'])
                file_result["results"].append(result)
                if not args.json:
                    print(f"✅ Successfully created {parsed_obj.kind} service: {display_job_id}")
                    print(f"📊 Name: {result['name']}")
                    print(f"📦 Namespace: {result['namespace']}")
                    if 'resources' in result:
                        print(f"🖥️  Resources: {result['resources']}")
                    
                    # Display Access Methods
                    print("\n🌐 Access Methods:")
                    
                    try:
                        from gpuctl.client.base_client import KubernetesClient
                        
                        # Create Kubernetes client to get service and node info
                        k8s_client = KubernetesClient()
                        
                        # Get Service info - use the actual namespace from result
                        service_namespace = result.get('namespace', 'default')
                        service_base_name = result['name']
                        
                        # Get Service
                        service = k8s_client.core_v1.read_namespaced_service(
                            name=f"svc-{service_base_name}",
                            namespace=service_namespace
                        )
                        service_data = service.to_dict()
                        
                        # Get Node IP
                        nodes = k8s_client.core_v1.list_node()
                        node_items = nodes.items
                        node_ip = 'N/A'
                        if node_items:
                            node_dict = node_items[0].to_dict()
                            node_addresses = node_dict.get('status', {}).get('addresses', [])
                            for addr in node_addresses:
                                if addr.get('type') == 'InternalIP':
                                    node_ip = addr.get('address')
                                    break
                        
                        # Get Service port info
                        node_port = service_data['spec']['ports'][0]['node_port'] if service_data['spec']['ports'] and 'node_port' in service_data['spec']['ports'][0] else 'N/A'
                        service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                        target_port = service_data['spec']['ports'][0]['target_port'] if service_data['spec']['ports'] else 'N/A'
                        
                        # Method 1: Access via Pod IP
                        print(f"   1. Pod IP Access:")
                        print(f"      - Pod is initializing, IP will be available once running")
                        print(f"      - Expected Port: {target_port if target_port != 'N/A' else service_port}")
                        
                        # Method 2: Access via NodePort
                        print(f"   2. NodePort Access:")
                        print(f"      - Node IP: {node_ip}")
                        print(f"      - NodePort: {node_port}")
                        if node_port != 'N/A':
                            print(f"      - Access: curl http://{node_ip}:{node_port}")
                        else:
                            print(f"      - NodePort not available")
                    except Exception as e:
                        print(f"      - Access methods information not available yet")
            elif parsed_obj.kind == "notebook":
                handler = NotebookKind()
                result = handler.create_notebook(parsed_obj, final_namespace)
                # Display job_id with prefix removed
                display_job_id = remove_prefix(result['job_id'])
                file_result["results"].append(result)
                if not args.json:
                    print(f"✅ Successfully created {parsed_obj.kind} job: {display_job_id}")
                    print(f"📊 Name: {result['name']}")
                    print(f"📦 Namespace: {result['namespace']}")
                    if 'resources' in result:
                        print(f"🖥️  Resources: {result['resources']}")
                    
                    # Display Access Methods
                    print("\n🌐 Access Methods:")
                    
                    try:
                        from gpuctl.client.base_client import KubernetesClient
                        
                        # Create Kubernetes client to get service and node info
                        k8s_client = KubernetesClient()
                        
                        # Get Service info - use the actual namespace from result
                        service_namespace = result.get('namespace', 'default')
                        service_base_name = result['name']
                        
                        # Get Service
                        service = k8s_client.core_v1.read_namespaced_service(
                            name=f"svc-{service_base_name}",
                            namespace=service_namespace
                        )
                        service_data = service.to_dict()
                        
                        # Get Node IP
                        nodes = k8s_client.core_v1.list_node()
                        node_items = nodes.items
                        node_ip = 'N/A'
                        if node_items:
                            node_dict = node_items[0].to_dict()
                            node_addresses = node_dict.get('status', {}).get('addresses', [])
                            for addr in node_addresses:
                                if addr.get('type') == 'InternalIP':
                                    node_ip = addr.get('address')
                                    break
                        
                        # Get Service port info
                        node_port = service_data['spec']['ports'][0]['node_port'] if service_data['spec']['ports'] and 'node_port' in service_data['spec']['ports'][0] else 'N/A'
                        service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                        target_port = service_data['spec']['ports'][0]['target_port'] if service_data['spec']['ports'] else 'N/A'
                        
                        # Method 1: Access via Pod IP
                        print(f"   1. Pod IP Access:")
                        print(f"      - Pod is initializing, IP will be available once running")
                        print(f"      - Expected Port: {target_port if target_port != 'N/A' else service_port}")
                        
                        # Method 2: Access via NodePort
                        print(f"   2. NodePort Access:")
                        print(f"      - Node IP: {node_ip}")
                        print(f"      - NodePort: {node_port}")
                        if node_port != 'N/A':
                            print(f"      - Access: curl http://{node_ip}:{node_port}")
                        else:
                            print(f"      - NodePort not available")
                    except Exception as e:
                        print(f"      - Access methods information not available yet")
            elif parsed_obj.kind == "compute":
                from gpuctl.kind.compute_kind import ComputeKind
                handler = ComputeKind()
                result = handler.create_compute_service(parsed_obj, final_namespace)
                # Display job_id with prefix removed
                display_job_id = remove_prefix(result['job_id'])
                file_result["results"].append(result)
                if not args.json:
                    print(f"✅ Successfully created {parsed_obj.kind} service: {display_job_id}")
                    print(f"📊 Name: {result['name']}")
                    print(f"📦 Namespace: {result['namespace']}")
                    if 'resources' in result:
                        print(f"🖥️  Resources: {result['resources']}")
                    
                    # Display Access Methods
                    print("\n🌐 Access Methods:")
                    
                    try:
                        from gpuctl.client.base_client import KubernetesClient
                        
                        # Create Kubernetes client to get service and node info
                        k8s_client = KubernetesClient()
                        
                        # Get Service info - use the actual namespace from result
                        service_namespace = result.get('namespace', 'default')
                        service_base_name = result['name']
                        
                        # Get Service
                        service = k8s_client.core_v1.read_namespaced_service(
                            name=f"svc-{service_base_name}",
                            namespace=service_namespace
                        )
                        service_data = service.to_dict()
                        
                        # Get Node IP
                        nodes = k8s_client.core_v1.list_node()
                        node_items = nodes.items
                        node_ip = 'N/A'
                        if node_items:
                            node_dict = node_items[0].to_dict()
                            node_addresses = node_dict.get('status', {}).get('addresses', [])
                            for addr in node_addresses:
                                if addr.get('type') == 'InternalIP':
                                    node_ip = addr.get('address')
                                    break
                        
                        # Get Service port info
                        node_port = service_data['spec']['ports'][0]['node_port'] if service_data['spec']['ports'] and 'node_port' in service_data['spec']['ports'][0] else 'N/A'
                        service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                        target_port = service_data['spec']['ports'][0]['target_port'] if service_data['spec']['ports'] else 'N/A'
                        
                        # Method 1: Access via Pod IP
                        print(f"   1. Pod IP Access:")
                        print(f"      - Pod is initializing, IP will be available once running")
                        print(f"      - Expected Port: {target_port if target_port != 'N/A' else service_port}")
                        
                        # Method 2: Access via NodePort
                        print(f"   2. NodePort Access:")
                        print(f"      - Node IP: {node_ip}")
                        print(f"      - NodePort: {node_port}")
                        if node_port != 'N/A':
                            print(f"      - Access: curl http://{node_ip}:{node_port}")
                        else:
                            print(f"      - NodePort not available")
                    except Exception as e:
                        print(f"      - Access methods information not available yet")
            elif parsed_obj.kind == "quota":
                # 处理quota类型，调用quota创建命令
                from gpuctl.cli.quota import create_quota_command
                # 创建一个简化的args对象，只包含quota命令需要的参数
                from argparse import Namespace
                quota_args = Namespace()
                quota_args.file = [file_path]  # 确保是列表格式
                quota_args.namespace = args.namespace
                quota_args.json = args.json  # Pass json flag to quota command
                create_quota_command(quota_args)
            elif parsed_obj.kind == "pool" or parsed_obj.kind == "resource":
                # Resource pool creation logic
                from gpuctl.client.pool_client import PoolClient
                client = PoolClient()
                
                # Build resource pool configuration
                pool_config = {
                    "name": parsed_obj.pool.name,
                    "description": parsed_obj.pool.description,
                    "nodes": list(parsed_obj.nodes.keys())
                }
                
                # Create resource pool
                result = client.create_pool(pool_config)
                file_result["results"].append(result)
                if not args.json:
                    print(f"✅ Successfully created resource pool: {result['name']}")
                    print(f"📊 Description: {parsed_obj.pool.description}")
                    print(f"📦 Node count: {len(parsed_obj.nodes)}")
                    print(f"📋 Status: {result['status']}")
            elif parsed_obj.kind == "quota":
                from gpuctl.cli.quota import create_quota_command
                import argparse
                quota_args = argparse.Namespace(file=[args.file[0]])
                return create_quota_command(quota_args)
            else:
                error = {"error": f"Unsupported kind: {parsed_obj.kind}"}
                file_result["results"].append(error)
                if not args.json:
                    print(f"❌ Unsupported kind: {parsed_obj.kind}")
                    return 1
            
            all_results.append(file_result)

        if args.json:
            print(json.dumps(all_results, indent=2))

        return 0
    except ParserError as e:
        error = {"error": f"Parser error: {str(e)}"}
        if args.json:
            import json
            print(json.dumps(error, indent=2))
        else:
            print(f"❌ Parser error: {e}")
        return 1
    except ValueError as e:
        error = {"error": str(e)}
        if args.json:
            import json
            print(json.dumps(error, indent=2))
        else:
            print(f"❌ {e}")
        return 1
    except Exception as e:
        error = {"error": f"Unexpected error: {str(e)}"}
        if args.json:
            import json
            print(json.dumps(error, indent=2))
        else:
            print(f"❌ Unexpected error: {e}")
        return 1


def apply_job_command(args):
    """Apply job command (create or update)"""
    try:
        import json
        all_results = []
        
        for file_path in args.file:
            if not args.json:
                print(f"\n📝 Applying file: {file_path}")
            
            parsed_obj = BaseParser.parse_yaml_file(file_path)
            file_result = {
                "file": file_path,
                "kind": parsed_obj.kind,
                "results": []
            }
            
            # Determine the final namespace: use YAML-specified first, then CLI arg, then default
            yaml_namespace = getattr(parsed_obj, 'job', None) and getattr(parsed_obj.job, 'namespace', None)
            final_namespace = yaml_namespace or args.namespace
            
            # Check if namespace has quota configured (except for quota and pool/resource kinds)
            if parsed_obj.kind not in ["quota", "pool", "resource"]:
                from gpuctl.client.quota_client import QuotaClient
                quota_client = QuotaClient()
                if not quota_client.namespace_has_quota(final_namespace):
                    error = {"error": f"Namespace '{final_namespace}' does not have quota configured. Please create quota for this namespace first."}
                    file_result["results"].append(error)
                    if args.json:
                        import json
                        print(json.dumps(error, indent=2))
                    else:
                        print(f"❌ Namespace '{final_namespace}' does not have quota configured. Please create quota for this namespace first.")
                    return 1
            
            if parsed_obj.kind == "training":
                from gpuctl.kind.training_kind import TrainingKind
                handler = TrainingKind()
                job_client = JobClient()
                
                job_name = add_prefix(parsed_obj.job.name, "training")
                existing = job_client.get_job(job_name, args.namespace)
                
                if existing:
                    action = "update"
                    if not args.json:
                        print(f"🔄 Updating {parsed_obj.kind} job: {remove_prefix(job_name)}")
                    result = handler.update_training_job(parsed_obj, args.namespace)
                else:
                    action = "create"
                    if not args.json:
                        print(f"✅ Creating {parsed_obj.kind} job: {remove_prefix(job_name)}")
                    result = handler.create_training_job(parsed_obj, args.namespace)
                
                display_job_id = remove_prefix(result['job_id'])
                result["action"] = action
                file_result["results"].append(result)
                if not args.json:
                    print(f"📊 Name: {result['name']}")
                    print(f"📦 Namespace: {result['namespace']}")
                    if 'resources' in result:
                        print(f"🖥️  Resources: {result['resources']}")
                    
            elif parsed_obj.kind == "inference":
                from gpuctl.kind.inference_kind import InferenceKind
                handler = InferenceKind()
                job_client = JobClient()
                
                job_name = add_prefix(parsed_obj.job.name, "inference")
                existing = job_client.get_job(job_name, args.namespace)
                
                if existing:
                    action = "update"
                    if not args.json:
                        print(f"🔄 Updating {parsed_obj.kind} service: {remove_prefix(job_name)}")
                    result = handler.update_inference_service(parsed_obj, args.namespace)
                else:
                    action = "create"
                    if not args.json:
                        print(f"✅ Creating {parsed_obj.kind} service: {remove_prefix(job_name)}")
                    result = handler.create_inference_service(parsed_obj, args.namespace)
                
                display_job_id = remove_prefix(result['job_id'])
                result["action"] = action
                file_result["results"].append(result)
                if not args.json:
                    print(f"📊 Name: {result['name']}")
                    print(f"📦 Namespace: {result['namespace']}")
                    if 'resources' in result:
                        print(f"🖥️  Resources: {result['resources']}")
                    
            elif parsed_obj.kind == "notebook":
                from gpuctl.kind.notebook_kind import NotebookKind
                handler = NotebookKind()
                job_client = JobClient()
                
                job_name = add_prefix(parsed_obj.job.name, "notebook")
                existing = job_client.get_job(job_name, args.namespace)
                
                if existing:
                    action = "update"
                    if not args.json:
                        print(f"🔄 Updating {parsed_obj.kind} job: {remove_prefix(job_name)}")
                    result = handler.update_notebook(parsed_obj, args.namespace)
                else:
                    action = "create"
                    if not args.json:
                        print(f"✅ Creating {parsed_obj.kind} job: {remove_prefix(job_name)}")
                    result = handler.create_notebook(parsed_obj, args.namespace)
                
                display_job_id = remove_prefix(result['job_id'])
                result["action"] = action
                file_result["results"].append(result)
                if not args.json:
                    print(f"📊 Name: {result['name']}")
                    print(f"📦 Namespace: {result['namespace']}")
                    if 'resources' in result:
                        print(f"🖥️  Resources: {result['resources']}")
                    
            elif parsed_obj.kind == "compute":
                from gpuctl.kind.compute_kind import ComputeKind
                handler = ComputeKind()
                job_client = JobClient()
                
                job_name = add_prefix(parsed_obj.job.name, "compute")
                existing = job_client.get_job(job_name, args.namespace)
                
                if existing:
                    action = "update"
                    if not args.json:
                        print(f"🔄 Updating {parsed_obj.kind} service: {remove_prefix(job_name)}")
                    result = handler.update_compute_service(parsed_obj, args.namespace)
                else:
                    action = "create"
                    if not args.json:
                        print(f"✅ Creating {parsed_obj.kind} service: {remove_prefix(job_name)}")
                    result = handler.create_compute_service(parsed_obj, args.namespace)
                
                display_job_id = remove_prefix(result['job_id'])
                result["action"] = action
                file_result["results"].append(result)
                if not args.json:
                    print(f"📊 Name: {result['name']}")
                    print(f"📦 Namespace: {result['namespace']}")
                    if 'resources' in result:
                        print(f"🖥️  Resources: {result['resources']}")
                    
            elif parsed_obj.kind == "pool" or parsed_obj.kind == "resource":
                from gpuctl.client.pool_client import PoolClient
                client = PoolClient()
                
                existing = client.get_pool(parsed_obj.pool.name)
                
                pool_config = {
                    "name": parsed_obj.pool.name,
                    "description": parsed_obj.pool.description,
                    "nodes": list(parsed_obj.nodes.keys())
                }
                
                if existing:
                    action = "update"
                    if not args.json:
                        print(f"🔄 Updating resource pool: {parsed_obj.pool.name}")
                    result = client.update_pool(pool_config)
                else:
                    action = "create"
                    if not args.json:
                        print(f"✅ Creating resource pool: {parsed_obj.pool.name}")
                    result = client.create_pool(pool_config)
                
                result["action"] = action
                file_result["results"].append(result)
                if not args.json:
                    print(f"📊 Description: {parsed_obj.metadata.description}")
                    print(f"📦 Node count: {len(parsed_obj.nodes)}")
                    print(f"📋 Status: {result['status']}")
                
            elif parsed_obj.kind == "quota":
                from gpuctl.cli.quota import apply_quota_command as quota_apply
                import argparse
                quota_args = argparse.Namespace(file=[file_path], json=args.json)
                return quota_apply(quota_args)
                
            else:
                error = {"error": f"Unsupported kind: {parsed_obj.kind}", "file": file_path}
                file_result["results"].append(error)
                if not args.json:
                    print(f"❌ Unsupported kind: {parsed_obj.kind}")
                    return 1
            
            all_results.append(file_result)

        if args.json:
            print(json.dumps(all_results, indent=2))

        return 0
    except ParserError as e:
        error = {"error": f"Parser error: {str(e)}"}
        if args.json:
            import json
            print(json.dumps(error, indent=2))
        else:
            print(f"❌ Parser error: {e}")
        return 1
    except ValueError as e:
        error = {"error": str(e)}
        if args.json:
            import json
            print(json.dumps(error, indent=2))
        else:
            print(f"❌ {e}")
        return 1
    except Exception as e:
        error = {"error": f"Unexpected error: {str(e)}"}
        if args.json:
            import json
            print(json.dumps(error, indent=2))
        else:
            print(f"❌ Unexpected error: {e}")
        return 1


def get_jobs_command(args):
    """Get jobs list command"""
    try:
        client = JobClient()
        
        # Build label filter criteria
        labels = {}
        if args.pool:
            labels["g8s.host/pool"] = args.pool
        if args.kind:
            labels["g8s.host/job-type"] = args.kind
        
        # Call API to get jobs list with filter criteria
        # 使用 include_pods=True 获取 Pod 资源，而不是 Deployment 或 StatefulSet 等高级资源
        jobs = client.list_jobs(args.namespace, labels=labels, include_pods=True)
        
        # Helper function to calculate AGE
        def calculate_age(created_at_str):
            from datetime import datetime, timezone
            import math
            
            if not created_at_str:
                return "N/A"
            
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = now - created_at
            
            seconds = delta.total_seconds()
            
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                return f"{int(seconds/60)}m"
            elif seconds < 86400:
                return f"{int(seconds/3600)}h"
            else:
                return f"{int(seconds/86400)}d"
        
        # 处理作业数据，计算最终状态
        processed_jobs = []
        for job in jobs:
            # 当 include_pods=True 时，job 实际上是一个 Pod 资源
            age = calculate_age(job.get('creation_timestamp'))
            job_type = job['labels'].get('g8s.host/job-type', 'unknown')
            job_namespace = job.get('namespace', 'default')
            status_dict = job.get("status", {})
            
            # 计算详细状态，与 describe 命令保持一致
            status = status_dict.get("phase", "Unknown")
            
            # Full status sync with kubectl
            phase_to_status = {
                "Pending": "Pending",
                "Running": "Running",
                "Succeeded": "Succeeded",
                "Failed": "Failed",
                "Unknown": "Unknown",
                "Completed": "Completed",
                "Terminating": "Terminating",
                "Deleting": "Deleting"
            }
            
            status = phase_to_status.get(status, status)
            
            # Check for special conditions in container statuses
            container_statuses = status_dict.get("container_statuses", [])
            if container_statuses:
                for cs in container_statuses:
                    if hasattr(cs, 'state') and cs.state:
                        if hasattr(cs.state, 'waiting') and cs.state.waiting:
                            waiting_reason = cs.state.waiting.reason
                            waiting_message = cs.state.waiting.message or ""
                            status = _get_detailed_status(waiting_reason, waiting_message)
                            break
                        if hasattr(cs.state, 'terminated') and cs.state.terminated:
                            terminated_reason = cs.state.terminated.reason
                            if terminated_reason == "OOMKilled":
                                status = "OOMKilled"
                                break
                            elif terminated_reason == "Error":
                                status = "Error"
                                break
            
            # For get jobs command, keep the original phase status to match kubectl output
            # Only describe command should show detailed status like Unschedulable
            
            # 提取 Pod 名称并去除前缀
            pod_name = job['name']
            simplified_name = remove_prefix(pod_name)
            
            # NAME 列只保留实际的作业名称，去除随机字符串和后缀
            # 例如：test-nginx-848cbf4cf5-2h4ss -> test-nginx
            final_name = simplified_name
            parts = simplified_name.split('-')
            if len(parts) >= 3:
                third_part = parts[2] if len(parts) >= 3 else ''
                if third_part.isalnum() and len(third_part) >= 5:
                    final_name = '-'.join(parts[:2])
            
            processed_jobs.append({
                'job_id': simplified_name,  # 使用去除前缀的完整 Pod 名称作为 Job ID
                'name': final_name,  # 使用简化后的作业名称作为 NAME 列
                'namespace': job_namespace,
                'kind': job_type,
                'status': status,
                'age': age
            })
        
        # 如果指定了 --json 参数，输出 JSON 格式
        if args.json:
            import json
            print(json.dumps(processed_jobs, indent=2))
            return 0
        
        # Calculate column widths dynamically for text output
        headers = ['JOB ID', 'NAME', 'NAMESPACE', 'KIND', 'STATUS', 'AGE']
        col_widths = {'job_id': 10, 'name': 10, 'namespace': 10, 'kind': 10, 'status': 10, 'age': 10}
        
        # First pass: calculate max widths
        for row in processed_jobs:
            col_widths['job_id'] = max(col_widths['job_id'], len(row['job_id']))
            col_widths['name'] = max(col_widths['name'], len(row['name']))
            col_widths['namespace'] = max(col_widths['namespace'], len(row['namespace']))
            col_widths['kind'] = max(col_widths['kind'], len(row['kind']))
            col_widths['status'] = max(col_widths['status'], len(row['status']))
            col_widths['age'] = max(col_widths['age'], len(row['age']))
        
        # Print header
        header_line = f"{headers[0]:<{col_widths['job_id']}}  {headers[1]:<{col_widths['name']}}  {headers[2]:<{col_widths['namespace']}}  {headers[3]:<{col_widths['kind']}}  {headers[4]:<{col_widths['status']}}  {headers[5]:<{col_widths['age']}}"
        print(header_line)
        
        # Print rows
        for row in processed_jobs:
            print(f"{row['job_id']:<{col_widths['job_id']}}  {row['name']:<{col_widths['name']}}  {row['namespace']:<{col_widths['namespace']}}  {row['kind']:<{col_widths['kind']}}  {row['status']:<{col_widths['status']}}  {row['age']:<{col_widths['age']}}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting jobs: {e}")
        import traceback
        traceback.print_exc()
        return 1


def delete_job_command(args):
    """Delete job command"""
    try:
        import json
        client = JobClient()
        resource_type = None
        resource_name = None
        original_resource_name = None
        force = getattr(args, 'force', False)
        
        # Handle deletion by job_name
        job_name = getattr(args, 'job_name', None)
        if job_name:
            # delete job <job_name> command
            resource_name = job_name
            original_resource_name = resource_name
        elif args.file:
            # delete -f <yaml_file> command
            resource_type = None
            resource_name = None
            original_resource_name = None
            
            try:
                # Try full parsing (compatible with old logic)
                parsed_obj = BaseParser.parse_yaml_file(args.file)
                resource_type = parsed_obj.kind
                
                if resource_type in ["pool", "resource"]:
                    # Resource pool handling
                    if hasattr(parsed_obj, 'metadata') and hasattr(parsed_obj.metadata, 'name'):
                        resource_name = parsed_obj.metadata.name
                    elif hasattr(parsed_obj, 'pool') and hasattr(parsed_obj.pool, 'name'):
                        resource_name = parsed_obj.pool.name
                    else:
                        resource_name = args.file.replace('.yaml', '').replace('.yml', '')
                elif resource_type in ["training", "inference", "notebook", "compute"]:
                    # Job handling
                    if hasattr(parsed_obj, 'job') and hasattr(parsed_obj.job, 'name'):
                        resource_name = parsed_obj.job.name
                    else:
                        resource_name = args.file.replace('.yaml', '').replace('.yml', '')
                    original_resource_name = resource_name
            except Exception as e:
                # Full parsing failed, try simple YAML parsing to get necessary info
                import yaml
                with open(args.file, 'r') as f:
                    yaml_dict = yaml.safe_load(f)
                resource_type = yaml_dict['kind']
                
                if resource_type in ["pool", "resource"]:
                    # Resource pool handling
                    if 'metadata' in yaml_dict and 'name' in yaml_dict['metadata']:
                        resource_name = yaml_dict['metadata']['name']
                    elif 'pool' in yaml_dict and 'name' in yaml_dict['pool']:
                        resource_name = yaml_dict['pool']['name']
                    else:
                        resource_name = args.file.replace('.yaml', '').replace('.yml', '')
                elif resource_type in ["training", "inference", "notebook", "compute"]:
                    # Job handling
                    resource_name = yaml_dict['job']['name']
                    original_resource_name = resource_name
            
            # Handle resource pool deletion
            if resource_type in ["pool", "resource"]:
                # Delete resource pool
                from gpuctl.client.pool_client import PoolClient
                client = PoolClient()
                success = client.delete_pool(resource_name)
                if success:
                    result = {"status": "success", "message": f"Successfully deleted resource pool: {resource_name}", "resource_type": "pool"}
                    if args.json:
                        print(json.dumps(result, indent=2))
                    else:
                        print(f"✅ Successfully deleted resource pool: {resource_name}")
                    return 0
                else:
                    error = {"error": f"Resource pool not found: {resource_name}", "resource_type": "pool"}
                    if args.json:
                        print(json.dumps(error, indent=2))
                    else:
                        print(f"❌ Resource pool not found: {resource_name}")
                    return 1
        else:
            error = {"error": "Must provide YAML file path (-f/--file) or job name"}
            if args.json:
                print(json.dumps(error, indent=2))
            else:
                print("❌ Must provide YAML file path (-f/--file) or job name")
            return 1
        
        # Handle job deletion
        success = False
        
        # Extract base job name from full pod name
        # Format: base-name-deployment-hash-pod-suffix -> base-name
        base_resource_name = resource_name
        parts = resource_name.split("-")
        if len(parts) >= 3:
            third_part = parts[2] if len(parts) >= 3 else ''
            if third_part.isalnum() and len(third_part) >= 5:
                base_resource_name = '-'.join(parts[:2])
        
        # Get all namespaces to search
        namespaces_to_search = [args.namespace] + [ns for ns in client._get_all_gpuctl_namespaces() if ns != args.namespace]
        
        for ns in namespaces_to_search:
            # Get all jobs list in current namespace to query actual job type
            all_jobs = client.list_jobs(ns, include_pods=False)
            found_job = None
            
            # Find matching job in all jobs
            for job in all_jobs:
                job_name = job['name']
                # Check if matches original name or base name (without prefix)
                if remove_prefix(job_name) == resource_name or remove_prefix(job_name) == base_resource_name:
                    found_job = job
                    break
            
            if found_job:
                # Get actual job type and name from found job
                actual_job_type = found_job['labels'].get('g8s.host/job-type', 'unknown')
                actual_job_name = found_job['name']
                
                # Call appropriate delete method based on actual job type (delete entire Deployment/StatefulSet/Job)
                if actual_job_type == "training":
                    # Training job: delete Job
                    success = client.delete_job(actual_job_name, ns, force)
                elif actual_job_type == "inference" or actual_job_type == "compute":
                    # Inference or Compute job: delete Deployment and Service
                    # Generate complete Service name
                    service_name = f"svc-{base_resource_name}"
                    # Delete Deployment
                    deployment_deleted = client.delete_deployment(actual_job_name, ns, force)
                    # Delete Service
                    service_deleted = client.delete_service(service_name, ns)
                    success = deployment_deleted and service_deleted
                elif actual_job_type == "notebook":
                    # Notebook job: delete StatefulSet and Service
                    # Generate complete Service name
                    service_name = f"svc-{base_resource_name}"
                    # Delete StatefulSet
                    statefulset_deleted = client.delete_statefulset(actual_job_name, ns, force)
                    # Delete Service
                    service_deleted = client.delete_service(service_name, ns)
                    success = statefulset_deleted and service_deleted
                
                if success:
                    break
            else:
                # Try all possible prefixes in current namespace
                job_types = ["training", "inference", "compute", "notebook"]
                for job_type in job_types:
                    full_name = base_resource_name
                    if job_type == "training":
                        success = client.delete_job(full_name, ns, force)
                    elif job_type == "inference" or job_type == "compute":
                        deployment_deleted = client.delete_deployment(full_name, ns, force)
                        service_deleted = client.delete_service(f"svc-{base_resource_name}", ns)
                        success = deployment_deleted and service_deleted
                    elif job_type == "notebook":
                        statefulset_deleted = client.delete_statefulset(full_name, ns, force)
                        service_deleted = client.delete_service(f"svc-{base_resource_name}", ns)
                        success = statefulset_deleted and service_deleted
                    
                    if success:
                        break
                
                if success:
                    break
        
        if success:
            result = {
                "status": "success", 
                "message": f"Successfully {'force deleted' if force else 'deleted'} job: {original_resource_name}",
                "job_name": original_resource_name,
                "force": force
            }
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if force:
                    print(f"✅ Successfully force deleted job: {original_resource_name}")
                else:
                    print(f"✅ Successfully deleted job: {original_resource_name}")
            return 0
        else:
            error = {
                "error": f"Job not found: {original_resource_name}",
                "job_name": original_resource_name
            }
            if args.json:
                print(json.dumps(error, indent=2))
            else:
                print(f"❌ Job not found: {original_resource_name}")
            return 1

    except Exception as e:
        error = {"error": str(e)}
        if args.json:
            print(json.dumps(error, indent=2))
        else:
            print(f"❌ Error deleting resource: {e}")
        return 1


def logs_job_command(args):
    """Get job logs command"""
    try:
        # Get the actual pod name from deployment/replicaset
        job_name = args.job_name
        namespace = args.namespace
        
        # Check if the specified namespace exists
        def namespace_exists(ns):
            """Check if the specified namespace exists"""
            try:
                from gpuctl.client.base_client import KubernetesClient
                k8s_client = KubernetesClient()
                # Try to get the namespace directly
                k8s_client.core_v1.read_namespace(ns)
                return True
            except Exception as e:
                # Check if the error is about namespace not existing
                error_msg = str(e).lower()
                if "namespace not found" in error_msg or "namespaces \"" + ns + "\" not found" in error_msg or "not found" in error_msg:
                    return False
                # For other errors, assume namespace exists
                return True
        
        # Check if the specified namespace exists
        if not namespace_exists(namespace):
            if args.json:
                import json
                print(json.dumps({"error": f"Namespace '{namespace}' not found"}, indent=2))
            else:
                print(f"❌ Namespace '{namespace}' not found")
            return 1
        
        # First, try to use the provided name as a direct Pod name
        def try_direct_pod(ns):
            """Try to use the provided name as a direct Pod name"""
            try:
                from gpuctl.client.job_client import JobClient
                job_client = JobClient()
                
                # Get all pods in the namespace with the exact name
                try:
                    pods = job_client.list_pods(ns)
                    for pod in pods:
                        if pod.get('name') == job_name:
                            return pod, ns
                except FileNotFoundError:
                    # No pods found in this namespace, which is expected
                    pass
                except Exception as e:
                    # Ignore other errors (e.g., permission denied)
                    pass
                return None, None
            except Exception as e:
                return None, None
        
        # Extract base job name from full pod name
        # Format: base-name-deployment-hash-pod-suffix -> base-name
        base_job_name = job_name
        parts = job_name.split("-")
        if len(parts) >= 3:
            third_part = parts[2] if len(parts) >= 3 else ''
            if third_part.isalnum() and len(third_part) >= 5:
                base_job_name = '-'.join(parts[:2])
        
        # Helper function to get pod in a specific namespace using label
        def get_pod_by_label(ns):
            """Try to get pod in the specified namespace using label"""
            try:
                from gpuctl.client.job_client import JobClient
                job_client = JobClient()
                
                # Get all pods in the namespace with the matching label
                pods = job_client.list_pods(ns, labels={"app": base_job_name})
                
                # Get first running pod
                running_pod = None
                for pod in pods:
                    if pod.get('status', {}).get('phase') == 'Running':
                        running_pod = pod
                        break
                
                if not running_pod:
                    # If no running pod, get the first pending pod
                    for pod in pods:
                        running_pod = pod
                        break
                
                if running_pod:
                    return running_pod, ns
                
                return None, None
            except Exception as e:
                # Ignore errors for now, we'll try other namespaces
                return None, None
        
        # Try to get pod
        running_pod = None
        actual_namespace = None
        
        # 1. First try direct pod name in specified namespace
        running_pod, actual_namespace = try_direct_pod(namespace)
        
        if not running_pod:
            # 2. If not found, try by label in specified namespace
            running_pod, actual_namespace = get_pod_by_label(namespace)
        
        if not running_pod:
            # 3. If not found, get all gpuctl-managed namespaces and try each one
            try:
                from gpuctl.client.job_client import JobClient
                job_client = JobClient()
                gpuctl_namespaces = job_client._get_all_gpuctl_namespaces()
                
                for ns in gpuctl_namespaces:
                    if ns == namespace:
                        continue  # Skip the namespace we already tried
                    
                    # Try direct pod name first
                    running_pod, actual_namespace = try_direct_pod(ns)
                    if running_pod:
                        break
                    
                    # If not found, try by label
                    running_pod, actual_namespace = get_pod_by_label(ns)
                    if running_pod:
                        break
            except Exception as e:
                pass
        
        if not running_pod:
            if args.json:
                import json
                print(json.dumps({"error": f"No pods found for job: {args.job_name}"}, indent=2))
            else:
                print(f"❌ No pods found for job: {args.job_name}")
            return 1
        
        actual_pod_name = running_pod['name']
        
        log_client = LogClient()
        
        if args.follow:
            # Use streaming logs, continuously fetch
            try:
                logs = log_client.stream_job_logs(actual_pod_name, namespace=actual_namespace, pod_name=actual_pod_name)
                has_logs = False
                for log in logs:
                    if log == "No pods found for this job":
                        # We already know the pod exists, so ignore this message
                        continue
                    print(log)
                    has_logs = True
                if not has_logs:
                    if args.json:
                        import json
                        print(json.dumps({"message": f"No logs available for {args.job_name}. The Pod might be starting up or has no log output."}, indent=2))
                    else:
                        print(f"ℹ️  No logs available for {args.job_name}. The Pod might be starting up or has no log output.")
            except KeyboardInterrupt:
                if args.json:
                    import json
                    print(json.dumps({"message": "Log streaming stopped by user"}, indent=2))
                else:
                    print(f"\n👋 Log streaming stopped by user")
                return 0
            except Exception as e:
                # If there's any other error, assume no logs available
                if args.json:
                    import json
                    print(json.dumps({"message": f"No logs available for {args.job_name}. The Pod might be starting up or has no log output."}, indent=2))
                else:
                    print(f"ℹ️  No logs available for {args.job_name}. The Pod might be starting up or has no log output.")
        else:
            # Get logs once
            try:
                logs = log_client.get_job_logs(actual_pod_name, namespace=actual_namespace, tail=100, pod_name=actual_pod_name)
                if not logs or logs == ["No pods found for this job"]:
                    if args.json:
                        import json
                        print(json.dumps({"message": f"No logs available for {args.job_name}. The Pod might be starting up or has no log output."}, indent=2))
                    else:
                        print(f"ℹ️  No logs available for {args.job_name}. The Pod might be starting up or has no log output.")
                else:
                    if args.json:
                        import json
                        print(json.dumps({
                            "logs": logs,
                            "pod_name": actual_pod_name,
                            "namespace": actual_namespace
                        }, indent=2))
                    else:
                        for log in logs:
                            print(log)
            except Exception as e:
                # If there's any error, assume no logs available
                if args.json:
                    import json
                    print(json.dumps({"message": f"No logs available for {args.job_name}. The Pod might be starting up or has no log output."}, indent=2))
                else:
                    print(f"ℹ️  No logs available for {args.job_name}. The Pod might be starting up or has no log output.")
        
        return 0
    except KeyboardInterrupt:
        if args.json:
            import json
            print(json.dumps({"message": "Log streaming stopped by user"}, indent=2))
        return 0
    except Exception as e:
        if args.json:
            import json
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"❌ Error getting logs: {e}")
        return 1





def describe_job_command(args):
    """Describe job details command"""
    # Calculate AGE helper function, defined at the beginning for both JSON and text output
    def calculate_age(created_at_str):
        from datetime import datetime, timezone
        if not created_at_str:
            return "N/A"
        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - created_at
        seconds = delta.total_seconds()
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m"
        elif seconds < 86400:
            return f"{int(seconds/3600)}h"
        else:
            return f"{int(seconds/86400)}d"
    
    try:
        from gpuctl.client.job_client import JobClient
        client = JobClient()
        job = None
        
        # Try to get job directly
        job = client.get_job(args.job_id, args.namespace)
        
        if not job:
            # Get all jobs including Pod instances to query actual job
            all_jobs = client.list_jobs(args.namespace, include_pods=True)
            found_job = None
            
            # Find matching job in all jobs
            for job_item in all_jobs:
                job_name = job_item['name']
                # Check if matches full name or original name (without prefix)
                if job_name == args.job_id or remove_prefix(job_name) == args.job_id:
                    found_job = job_item
                    break
            
            if found_job:
                job = found_job
            else:
                # If still not found, get all gpuctl-managed namespaces and try each one
                try:
                    from gpuctl.client.job_client import JobClient
                    k8s_client = JobClient()
                    
                    # Get all gpuctl-managed namespaces
                    gpuctl_namespaces = k8s_client._get_all_gpuctl_namespaces()
                    
                    # Try to find the pod by exact name in gpuctl-managed namespaces
                    for ns in gpuctl_namespaces:
                        try:
                            # Try direct pod lookup in gpuctl-managed namespace
                            pod = k8s_client.core_v1.read_namespaced_pod(args.job_id, ns)
                            # Convert pod to dict format
                            pod_dict = k8s_client._pod_to_dict(pod)
                            job = pod_dict
                            break
                        except Exception:
                            # Pod not found in this namespace, continue searching
                            pass
                except Exception:
                    pass
                
                if not job:
                    # If still not found, check if it's a full pod name with hash suffix
                    # Format: base-name-deployment-hash-pod-suffix -> extract base-name
                    parts = args.job_id.split("-")
                    if len(parts) >= 3:
                        third_part = parts[2] if len(parts) >= 3 else ''
                        if third_part.isalnum() and len(third_part) >= 5:
                            # This is likely a full pod name, extract base name
                            base_job_name = '-'.join(parts[:2])
                            
                            # Try to get job with base name
                            job = client.get_job(base_job_name, args.namespace)
                            
                            if not job:
                                # Try with prefixes for base name
                                job_types = ["training", "inference", "notebook", "compute"]
                                found = False
                                for job_type in job_types:
                                    prefixed_job_id = add_prefix(base_job_name, job_type)
                                    job = client.get_job(prefixed_job_id, args.namespace)
                                    if job:
                                        found = True
                                        break
                                
                                if not found:
                                    # Also check all_jobs for base name match
                                    for job_item in all_jobs:
                                        job_name = job_item['name']
                                        # Check if job_item's name contains base_job_name
                                        if base_job_name in job_name or remove_prefix(job_name) == base_job_name:
                                            found_job = job_item
                                            break
                                    
                                    if found_job:
                                        job = found_job
            
            if not job:
                if args.json:
                    import json
                    print(json.dumps({"error": f"Job not found: {args.job_id}"}, indent=2))
                else:
                    print(f"❌ Job not found: {args.job_id}")
                return 1
            
        # 输出 JSON 格式
        if args.json:
            import json
            # 处理作业数据，移除 prefix
            processed_job = {
                "job_id": remove_prefix(job.get('name', 'N/A')),
                "name": remove_prefix(job.get('name', 'N/A')),
                "namespace": job.get('namespace', 'default'),
                "kind": job.get('labels', {}).get('g8s.host/job-type', 'unknown'),
                "status": "Unknown",
                "age": calculate_age(job.get('creation_timestamp')),
                "started": job.get('start_time', 'N/A'),
                "completed": job.get('completion_time', 'N/A'),
                "priority": job.get('labels', {}).get('g8s.host/priority', 'medium'),
                "pool": job.get('labels', {}).get('g8s.host/pool', 'default'),
                "resources": job.get('resources', {}),
                "metrics": job.get('metrics', {})
            }
            
            # 计算状态
            status_dict = job.get('status', {})
            pods = job.get('pods', [])
            
            # 初始化状态为Unknown
            status = "Unknown"
            
            # 处理单个 Pod 情况（当 include_pods=True 时，job 本身就是 Pod 对象）
            if "phase" in status_dict:
                # 直接使用 Pod 的 phase 作为初始状态
                pod_phase = status_dict.get("phase", "Unknown")
                
                # Full status sync with kubectl
                phase_to_status = {
                    "Pending": "Pending",
                    "Running": "Running",
                    "Succeeded": "Succeeded",
                    "Failed": "Failed",
                    "Unknown": "Unknown",
                    "Completed": "Completed",
                    "Terminating": "Terminating",
                    "Deleting": "Deleting"
                }
                
                status = phase_to_status.get(pod_phase, pod_phase)
                
                # For describe job command, keep the original phase status to match kubectl output
                # No need to show detailed status like Unschedulable
                # Skip container status checking to maintain original phase
            elif pods:
                # 处理多个 Pod 情况
                # 统计不同状态的 Pod 数量
                pod_status_count = {}
                for pod in pods:
                    pod_phase = pod.get('status', {}).get('phase', 'Unknown')
                    pod_status_count[pod_phase] = pod_status_count.get(pod_phase, 0) + 1
                
                # 基于 Pod 状态更新作业状态，与 kubectl 对齐
                if pod_status_count.get('Running', 0) > 0:
                    status = "Running"
                elif pod_status_count.get('Pending', 0) > 0:
                    status = "Pending"
                elif pod_status_count.get('Succeeded', 0) > 0:
                    status = "Succeeded"
                elif pod_status_count.get('Failed', 0) > 0:
                    status = "Failed"
            else:
                # 如果没有 Pod 信息，再根据资源类型判断状态
                if "active" in status_dict and "succeeded" in status_dict and "failed" in status_dict:
                    if status_dict["succeeded"] > 0:
                        status = "Succeeded"
                    elif status_dict["failed"] > 0:
                        status = "Failed"
                    elif status_dict["active"] > 0:
                        status = "Running"
                    else:
                        status = "Pending"
                elif "ready_replicas" in status_dict:
                    ready_replicas = status_dict.get("ready_replicas", 0)
                    if "unavailable_replicas" in status_dict:
                        unavailable_replicas = status_dict.get("unavailable_replicas", 0)
                        total_replicas = ready_replicas + unavailable_replicas
                        if total_replicas == 0:
                            status = "Pending"
                        elif ready_replicas > 0:
                            status = "Running"
                        else:
                            status = "Pending"
                    else:
                        current_replicas = status_dict.get("current_replicas", 0)
                        replicas = status_dict.get("replicas", 0)
                        if ready_replicas == replicas and replicas > 0:
                            status = "Running"
                        elif ready_replicas > 0:
                            status = "Running"
                        else:
                            status = "Pending"
            
            # 设置最终状态
            processed_job['status'] = status
            
            print(json.dumps(processed_job, indent=2))
            return 0
        
        # 输出文本格式
        # Print job details with prefix removed
        display_name = remove_prefix(job.get('name', 'N/A'))
        print(f"📋 Job Details: {display_name}")
        print(f"📊 Name: {display_name}")
        
        # Get job type and status
        job_type = job.get('labels', {}).get('g8s.host/job-type', 'unknown')
        status_dict = job.get('status', {})
        
        # Display real Pod status (phase)
        pod_phase = status_dict.get("phase", "Unknown")
        
        # Full status sync with kubectl
        phase_to_status = {
            "Pending": "Pending",
            "Running": "Running",
            "Succeeded": "Succeeded",
            "Failed": "Failed",
            "Unknown": "Unknown",
            "Completed": "Completed",
            "Terminating": "Terminating",
            "Deleting": "Deleting"
        }
        
        if pod_phase in phase_to_status:
            status = phase_to_status[pod_phase]
        else:
            status = pod_phase
        
        # Check for special conditions
        # Calculate AGE
        # For describe job command, keep the original phase status to match kubectl output
        # No need to show detailed status like Unschedulable
        # Skip all status modifications, just use the original phase
        def calculate_age(created_at_str):
            from datetime import datetime, timezone
            if not created_at_str:
                return "N/A"
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = now - created_at
            seconds = delta.total_seconds()
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                return f"{int(seconds/60)}m"
            elif seconds < 86400:
                return f"{int(seconds/3600)}h"
            else:
                return f"{int(seconds/86400)}d"
        
        age = calculate_age(job.get('creation_timestamp'))
        
        print(f"🗂️  Kind: {job_type}")
        print(f"📈 Status: {status}")
        print(f"⏰ Age: {age}")
        print(f"🔧 Started: {job.get('start_time', 'N/A')}")
        print(f"🏁 Completed: {job.get('completion_time', 'N/A')}")
        print(f"📋 Priority: {job.get('labels', {}).get('g8s.host/priority', 'medium')}")
        print(f"🖥️  Pool: {job.get('labels', {}).get('g8s.host/pool', 'default')}")
        
        full_job_name = job.get('name', '')
        if full_job_name:
            try:
                # Create Kubernetes client to get events
                from gpuctl.client.base_client import KubernetesClient
                k8s_client = KubernetesClient()
                
                # Get events for this pod
                field_selector = f"involvedObject.name={full_job_name},involvedObject.kind=Pod"
                events = k8s_client.core_v1.list_namespaced_event(
                    namespace=args.namespace,
                    field_selector=field_selector,
                    limit=10
                )
                
                if events.items:
                    print(f"\n📋 Events:")
                    
                    for i, event in enumerate(events.items):
                        event_type = event.type or 'Normal'
                        reason = event.reason or '-'
                        
                        timestamp = event.last_timestamp or event.first_timestamp or event.event_time
                        if timestamp:
                            timestamp_str = timestamp.isoformat()
                            if '.' in timestamp_str:
                                timestamp_str = timestamp_str.split('.')[0] + 'Z'
                        else:
                            timestamp_str = None
                        age = _format_event_age(timestamp_str)
                        
                        source = event.source.component if event.source and event.source.component else '-'
                        message = event.message or '-'
                        
                        print(f"  [{age}] {event_type} {reason}")
                        print(f"    From: {source}")
                        print(f"    Message: {message}")
                        
                        if i < len(events.items) - 1:
                            print()
            except Exception:
                pass
        
        if 'resources' in job:
            print("\n💻 Resources:")
            resources = job['resources']
            print(f"   GPU: {resources.get('gpu', 'N/A')}")
            print(f"   CPU: {resources.get('cpu', 'N/A')}")
            print(f"   Memory: {resources.get('memory', 'N/A')}")
            print(f"   GPU Type: {resources.get('gpu_type', 'N/A')}")
        
        if 'metrics' in job:
            print("\n📊 Metrics:")
            metrics = job['metrics']
            print(f"   GPU Utilization: {metrics.get('gpuUtilization', 'N/A')}%")
            print(f"   Memory Usage: {metrics.get('memoryUsage', 'N/A')}")
            print(f"   Throughput: {metrics.get('throughput', 'N/A')}")
        
        # Get and display access methods
        job_type = job.get('labels', {}).get('g8s.host/job-type', '')
        if job_type in ['inference', 'compute', 'notebook']:
            print("\n🌐 Access Methods:")
            
            # Get full job name and actual namespace from the job
            full_job_name = job.get('name', '')
            actual_namespace = job.get('namespace', args.namespace)
            
            # Extract base job name
            base_job_name = remove_prefix(full_job_name)
            
            # If this is a full pod name, extract the base name correctly
            parts = base_job_name.split('-')
            if len(parts) >= 3:
                third_part = parts[2] if len(parts) >= 3 else ''
                if third_part.isalnum() and len(third_part) >= 5:
                    # This is likely a full pod name, extract base name
                    base_job_name = '-'.join(parts[:2])
            
            # Extract service base name
            service_base_name = base_job_name
            
            # Handle different job types for service name extraction
            if job_type == 'notebook':
                # StatefulSet Pod format: base-name-index (e.g., new-test-notebook-job-0)
                parts = service_base_name.split('-')
                if len(parts) >= 2 and parts[-1].isdigit():
                    # Remove last numeric part
                    service_base_name = '-'.join(parts[:-1])
            elif len(service_base_name.split('-')) >= 3:
                # Deployment Pod format: base-name-deployment-hash-pod-suffix
                service_base_name = '-'.join(service_base_name.split('-')[:-2])
            
            # Get Service info first to get ports
            service_data = None
            service_found = True
            try:
                # Create Kubernetes client to get service
                from gpuctl.client.base_client import KubernetesClient
                k8s_client = KubernetesClient()
                
                # Get Service using actual namespace
                service = k8s_client.core_v1.read_namespaced_service(
                    name=f"svc-{service_base_name}",
                    namespace=actual_namespace
                )
                service_data = service.to_dict()
            except Exception as e:
                service_found = False
            
            # Method 1: Access via Pod IP
            print(f"   1. Pod IP Access:")
            try:
                # Create Kubernetes client to get pods
                from gpuctl.client.base_client import KubernetesClient
                k8s_client = KubernetesClient()
                
                # Get the specific pod we're describing by exact name and namespace
                pod = k8s_client.core_v1.read_namespaced_pod(
                    name=full_job_name,
                    namespace=actual_namespace
                )
                
                pod_dict = pod.to_dict()
                pod_status = pod_dict.get('status', {}).get('phase', 'Unknown')
                
                if pod_status == 'Running':
                    pod_ip = pod_dict['status'].get('pod_ip', 'N/A')
                    if service_found and service_data:
                        # Get Service port info
                        target_port = service_data['spec']['ports'][0]['target_port'] if service_data['spec']['ports'] else 'N/A'
                        service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                        pod_port = target_port if target_port != 'N/A' else service_port
                        print(f"      - Pod IP: {pod_ip}")
                        print(f"      - Port: {pod_port}")
                        print(f"      - Access: curl http://{pod_ip}:{pod_port}")
                    else:
                        print(f"      - Pod IP: {pod_ip}")
                else:
                    # Pod is not running, no IP available
                    print(f"      - Pod is {pod_status}, IP not available yet")
            except Exception as e:
                print(f"      - Failed to get pod info: {e}")
            
            # Method 2: Access via NodePort
            print(f"   2. NodePort Access:")
            if not service_found:
                # Service not found, show friendly message
                print(f"      - Service not available for this job")
            else:
                try:
                    if service_data:
                        # Get Service port info
                        node_port = service_data['spec']['ports'][0]['node_port'] if service_data['spec']['ports'] and 'node_port' in service_data['spec']['ports'][0] else 'N/A'
                        
                        # Get Node IP
                        from gpuctl.client.base_client import KubernetesClient
                        k8s_client = KubernetesClient()
                        
                        nodes = k8s_client.core_v1.list_node()
                        node_items = nodes.items
                        node_ip = 'N/A'
                        if node_items:
                            node_dict = node_items[0].to_dict()
                            node_addresses = node_dict.get('status', {}).get('addresses', [])
                            for addr in node_addresses:
                                if addr.get('type') == 'InternalIP':
                                    node_ip = addr.get('address')
                                    break
                        
                        # Check the specific pod's status
                        pod = k8s_client.core_v1.read_namespaced_pod(
                            name=full_job_name,
                            namespace=actual_namespace
                        )
                        pod_dict = pod.to_dict()
                        any_running = pod_dict.get('status', {}).get('phase') == 'Running'
                        
                        if any_running:
                            print(f"      - Node IP: {node_ip}")
                            print(f"      - NodePort: {node_port}")
                            if node_port != 'N/A':
                                print(f"      - Access: curl http://{node_ip}:{node_port}")
                            else:
                                print(f"      - NodePort not available")
                        else:
                            # No running pods, NodePort access not available yet
                            print(f"      - No running pods, NodePort access unavailable")
                    else:
                        print(f"      - No service found for this job")
                except Exception as e:
                    print(f"      - Failed to get service info: {e}")
        
        return 0
    except Exception as e:
        if args.json:
            import json
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"❌ Error describing job: {e}")
        return 1
