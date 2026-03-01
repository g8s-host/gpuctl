import sys
from gpuctl.parser.base_parser import BaseParser, ParserError
from gpuctl.kind.training_kind import TrainingKind
from gpuctl.kind.inference_kind import InferenceKind
from gpuctl.kind.notebook_kind import NotebookKind
from gpuctl.client.job_client import JobClient
from gpuctl.client.log_client import LogClient
from gpuctl.constants import (
    Kind, JOB_KINDS, NON_JOB_KINDS, KINDS_WITH_SERVICE,
    Labels, PHASE_TO_STATUS, DEFAULT_NAMESPACE, DEFAULT_POOL,
    K8sResourceType, KIND_TO_RESOURCE, infer_resource_type,
    Priority, DEFAULT_PRIORITY,
    svc_name, get_detailed_status,
)


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

def _get_job_name(labels: dict) -> str:
    """Get the original YAML job.name from K8s resource labels.

    - inference/notebook/compute pods have label ``app: {job.name}``
    - training pods have label ``job-name: {job.name}`` (set by K8s Job controller)

    Returns the YAML name, or empty string if labels are missing.
    """
    return labels.get(Labels.APP) or labels.get(Labels.JOB_NAME) or ''


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
            
            # Check if namespace exists (except for quota and pool/resource kinds)
            if parsed_obj.kind not in NON_JOB_KINDS:
                from gpuctl.client.base_client import KubernetesClient
                k8s_client = KubernetesClient()
                try:
                    k8s_client.core_v1.read_namespace(final_namespace)
                except Exception as e:
                    error = {"error": f"Namespace '{final_namespace}' does not exist. Please create the namespace first."}
                    file_result["results"].append(error)
                    if args.json:
                        import json
                        print(json.dumps(error, indent=2))
                    else:
                        print(f"❌ Namespace '{final_namespace}' does not exist. Please create the namespace first.")
                    return 1
            
            # Check if namespace has quota configured (except for quota and pool/resource kinds)
            if parsed_obj.kind not in NON_JOB_KINDS:
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
            
            # Check if pool exists and has nodes (except for quota and pool/resource kinds)
            if parsed_obj.kind not in NON_JOB_KINDS:
                pool_name = None
                if hasattr(parsed_obj, 'resources') and hasattr(parsed_obj.resources, 'pool'):
                    pool_name = parsed_obj.resources.pool
                elif hasattr(parsed_obj, 'job') and hasattr(parsed_obj.job, 'pool'):
                    pool_name = parsed_obj.job.pool
                
                from gpuctl.client.pool_client import PoolClient
                from gpuctl.client.base_client import KubernetesClient
                pool_client = PoolClient()
                k8s_client = KubernetesClient()
                
                if pool_name and pool_name != DEFAULT_POOL:
                    pool = pool_client.get_pool(pool_name)
                    if not pool:
                        error = {"error": f"Pool '{pool_name}' does not exist. Please create the pool first."}
                        file_result["results"].append(error)
                        if args.json:
                            import json
                            print(json.dumps(error, indent=2))
                        else:
                            print(f"❌ Pool '{pool_name}' does not exist. Please create the pool first.")
                        return 1
                    
                    if not pool.get('nodes') or len(pool.get('nodes')) == 0:
                        error = {"error": f"Pool '{pool_name}' does not have any nodes. Please add nodes to the pool first."}
                        file_result["results"].append(error)
                        if args.json:
                            import json
                            print(json.dumps(error, indent=2))
                        else:
                            print(f"❌ Pool '{pool_name}' does not have any nodes. Please add nodes to the pool first.")
                        return 1
                else:
                    nodes = k8s_client.core_v1.list_node()
                    nodes_without_pool = []
                    for node in nodes.items:
                        labels = node.metadata.labels or {}
                        if Labels.POOL not in labels:
                            nodes_without_pool.append(node.metadata.name)
                    
                    if len(nodes_without_pool) == 0:
                        error = {"error": "Default pool has no available nodes. All nodes are assigned to specific pools. Please specify a pool in your YAML or add nodes without pool labels."}
                        file_result["results"].append(error)
                        if args.json:
                            import json
                            print(json.dumps(error, indent=2))
                        else:
                            print(f"❌ Default pool has no available nodes. All nodes are assigned to specific pools.")
                            print(f"   Please specify a pool in your YAML or add nodes without pool labels.")
                        return 1
            
            # Check if a job with the same name already exists in the target namespace
            if parsed_obj.kind in JOB_KINDS:
                job_name = getattr(parsed_obj.job, 'name', None)
                if job_name:
                    try:
                        existing_jobs = JobClient().list_jobs(final_namespace, labels={}, include_pods=False)
                        for ej in existing_jobs:
                            if ej['name'] == job_name:
                                ej_kind = ej.get('labels', {}).get(Labels.JOB_TYPE, 'unknown')
                                error_msg = (
                                    f"Job '{job_name}' already exists in namespace '{final_namespace}' "
                                    f"(kind: {ej_kind}). "
                                    f"Use 'apply -f {file_path}' to update it, or delete it first."
                                )
                                if args.json:
                                    print(json.dumps({"error": error_msg}, indent=2))
                                else:
                                    print(f"❌ {error_msg}")
                                return 1
                    except Exception:
                        pass

            # Create appropriate handler based on type
            if parsed_obj.kind == Kind.TRAINING:
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
            elif parsed_obj.kind == Kind.INFERENCE:
                handler = InferenceKind()
                result = handler.create_inference_service(parsed_obj, final_namespace)
                display_job_id = remove_prefix(result['job_id'])
                file_result["results"].append(result)
                if not args.json:
                    print(f"✅ Successfully created {parsed_obj.kind} service: {display_job_id}")
                    print(f"📊 Name: {result['name']}")
                    print(f"📦 Namespace: {result['namespace']}")
                    if 'resources' in result:
                        print(f"🖥️  Resources: {result['resources']}")
                    
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
                            name=svc_name(service_base_name),
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
            elif parsed_obj.kind == Kind.NOTEBOOK:
                handler = NotebookKind()
                result = handler.create_notebook(parsed_obj, final_namespace)
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
                            name=svc_name(service_base_name),
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
            elif parsed_obj.kind == Kind.COMPUTE:
                from gpuctl.kind.compute_kind import ComputeKind
                handler = ComputeKind()
                result = handler.create_compute_service(parsed_obj, final_namespace)
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
                            name=svc_name(service_base_name),
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
                from gpuctl.cli.quota import create_quota_command
                from argparse import Namespace
                quota_args = Namespace()
                quota_args.file = [file_path]
                quota_args.namespace = args.namespace
                quota_args.json = args.json
                create_quota_command(quota_args)
            elif parsed_obj.kind in ("pool", "resource"):
                # Resource pool creation logic
                from gpuctl.client.pool_client import PoolClient
                client = PoolClient()
                
                # Build nodes config as a dictionary with gpuType information
                nodes_config = {}
                for node_name, node_config in parsed_obj.nodes.items():
                    nodes_config[node_name] = {"gpuType": node_config.gpu_type}
                
                # Build resource pool configuration
                pool_config = {
                    "name": parsed_obj.pool.name,
                    "description": parsed_obj.pool.description,
                    "nodes": nodes_config
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
            
            # Check if namespace exists (except for quota and pool/resource kinds)
            if parsed_obj.kind not in NON_JOB_KINDS:
                from gpuctl.client.base_client import KubernetesClient
                k8s_client = KubernetesClient()
                try:
                    k8s_client.core_v1.read_namespace(final_namespace)
                except Exception as e:
                    error = {"error": f"Namespace '{final_namespace}' does not exist. Please create the namespace first."}
                    file_result["results"].append(error)
                    if args.json:
                        import json
                        print(json.dumps(error, indent=2))
                    else:
                        print(f"❌ Namespace '{final_namespace}' does not exist. Please create the namespace first.")
                    return 1
            
            if parsed_obj.kind not in NON_JOB_KINDS:
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
            
            if parsed_obj.kind == Kind.TRAINING:
                from gpuctl.kind.training_kind import TrainingKind
                handler = TrainingKind()
                job_client = JobClient()
                
                job_name = add_prefix(parsed_obj.job.name, Kind.TRAINING)
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
                    
            elif parsed_obj.kind == Kind.INFERENCE:
                from gpuctl.kind.inference_kind import InferenceKind
                handler = InferenceKind()
                job_client = JobClient()
                
                job_name = add_prefix(parsed_obj.job.name, Kind.INFERENCE)
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
                    
            elif parsed_obj.kind == Kind.NOTEBOOK:
                from gpuctl.kind.notebook_kind import NotebookKind
                handler = NotebookKind()
                job_client = JobClient()
                
                job_name = add_prefix(parsed_obj.job.name, Kind.NOTEBOOK)
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
                    
            elif parsed_obj.kind == Kind.COMPUTE:
                from gpuctl.kind.compute_kind import ComputeKind
                handler = ComputeKind()
                job_client = JobClient()
                
                job_name = add_prefix(parsed_obj.job.name, Kind.COMPUTE)
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
                    
            elif parsed_obj.kind in ("pool", "resource"):
                from gpuctl.client.pool_client import PoolClient
                client = PoolClient()
                
                existing = client.get_pool(parsed_obj.pool.name)
                
                # Build nodes config as a dictionary with gpuType information
                nodes_config = {}
                for node_name, node_config in parsed_obj.nodes.items():
                    nodes_config[node_name] = {"gpuType": node_config.gpu_type}
                
                pool_config = {
                    "name": parsed_obj.pool.name,
                    "description": parsed_obj.pool.description,
                    "nodes": nodes_config
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
                    print(f"📊 Description: {parsed_obj.pool.description}")
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
        
        # Build label filter criteria (exclude job-type for now to get all pods)
        labels = {}
        
        # Call API to get jobs list with filter criteria
        # 使用 include_pods=True 获取 Pod 资源，而不是 Deployment 或 StatefulSet 等高级资源
        jobs = client.list_jobs(args.namespace, labels=labels, include_pods=True)
        
        # Filter jobs by kind if specified
        if args.kind:
            filtered_jobs = []
            for job in jobs:
                # Get job type from labels, or determine it like _pod_to_dict does
                job_type = job.get('labels', {}).get(Labels.JOB_TYPE, 'unknown')
                
                if job_type == 'unknown':
                    labels = job.get('labels', {})
                    if Labels.JOB_NAME in labels:
                        job_type = Kind.TRAINING
                    else:
                        job_type = Kind.COMPUTE
                
                if job_type == args.kind:
                    filtered_jobs.append(job)
            jobs = filtered_jobs
        
        # If pool is specified, filter jobs by nodes in the pool
        if args.pool:
            from gpuctl.client.pool_client import PoolClient
            pool_client = PoolClient()
            pool = pool_client.get_pool(args.pool)
            
            if pool:
                pool_nodes = pool.get('nodes', [])
                # Filter jobs that are running on nodes in the pool or are Pending
                filtered_jobs = []
                for job in jobs:
                    node_name = job.get('spec', {}).get('node_name')
                    job_status = job.get('status', {}).get('phase')
                    # Include jobs that are either on a pool node or are Pending
                    if node_name and node_name in pool_nodes or job_status == 'Pending':
                        filtered_jobs.append(job)
                jobs = filtered_jobs
        
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
            job_type = job['labels'].get(Labels.JOB_TYPE, 'unknown')
            job_namespace = job.get('namespace', DEFAULT_NAMESPACE)
            status_dict = job.get("status", {})
            
            status = status_dict.get("phase", "Unknown")
            status = PHASE_TO_STATUS.get(status, status)
            
            container_statuses = status_dict.get("container_statuses", [])
            if container_statuses:
                for cs in container_statuses:
                    if hasattr(cs, 'state') and cs.state:
                        if hasattr(cs.state, 'waiting') and cs.state.waiting:
                            waiting_reason = cs.state.waiting.reason
                            waiting_message = cs.state.waiting.message or ""
                            status = get_detailed_status(waiting_reason, waiting_message)
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
            
            pod_name = job['name']
            simplified_name = remove_prefix(pod_name)
            
            # NAME = YAML job.name, read from pod labels
            job_labels = job.get('labels', {})
            final_name = _get_job_name(job_labels) or simplified_name
            
            # 获取节点名称和 IP 地址
            node_name = job.get('spec', {}).get('node_name') or 'N/A'
            pod_ip = job.get('status', {}).get('pod_ip') or 'N/A'
            
            # 计算 READY 状态 (ready_containers/total_containers)
            container_statuses = status_dict.get("container_statuses", [])
            total_containers = len(container_statuses)
            ready_containers = 0
            if container_statuses:
                for cs in container_statuses:
                    if hasattr(cs, 'ready') and cs.ready:
                        ready_containers += 1
            ready_str = f"{ready_containers}/{total_containers}" if total_containers > 0 else "0/0"
            
            processed_jobs.append({
                'job_id': simplified_name,  # 使用去除前缀的完整 Pod 名称作为 Job ID
                'name': final_name,  # 使用简化后的作业名称作为 NAME 列
                'namespace': job_namespace,
                'kind': job_type,
                'status': status,
                'ready': ready_str,
                'node': node_name,
                'ip': pod_ip,
                'age': age
            })
        
        # 如果指定了 --json 参数，输出 JSON 格式
        if args.json:
            import json
            print(json.dumps(processed_jobs, indent=2))
            return 0
        
        # Calculate column widths dynamically for text output
        headers = ['JOB ID', 'NAME', 'NAMESPACE', 'KIND', 'STATUS', 'READY', 'NODE', 'IP', 'AGE']
        col_widths = {'job_id': 10, 'name': 10, 'namespace': 10, 'kind': 10, 'status': 10, 'ready': 8, 'node': 10, 'ip': 15, 'age': 10}
        
        # First pass: calculate max widths
        for row in processed_jobs:
            col_widths['job_id'] = max(col_widths['job_id'], len(row['job_id']))
            col_widths['name'] = max(col_widths['name'], len(row['name']))
            col_widths['namespace'] = max(col_widths['namespace'], len(row['namespace']))
            col_widths['kind'] = max(col_widths['kind'], len(row['kind']))
            col_widths['status'] = max(col_widths['status'], len(row['status']))
            col_widths['ready'] = max(col_widths['ready'], len(row['ready']))
            col_widths['node'] = max(col_widths['node'], len(row['node']))
            col_widths['ip'] = max(col_widths['ip'], len(row['ip']))
            col_widths['age'] = max(col_widths['age'], len(row['age']))
        
        # Print header
        header_line = f"{headers[0]:<{col_widths['job_id']}}  {headers[1]:<{col_widths['name']}}  {headers[2]:<{col_widths['namespace']}}  {headers[3]:<{col_widths['kind']}}  {headers[4]:<{col_widths['status']}}  {headers[5]:<{col_widths['ready']}}  {headers[6]:<{col_widths['node']}}  {headers[7]:<{col_widths['ip']}}  {headers[8]:<{col_widths['age']}}"
        print(header_line)
        
        # Print rows
        for row in processed_jobs:
            print(f"{row['job_id']:<{col_widths['job_id']}}  {row['name']:<{col_widths['name']}}  {row['namespace']:<{col_widths['namespace']}}  {row['kind']:<{col_widths['kind']}}  {row['status']:<{col_widths['status']}}  {row['ready']:<{col_widths['ready']}}  {row['node']:<{col_widths['node']}}  {row['ip']:<{col_widths['ip']}}  {row['age']:<{col_widths['age']}}")
        
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
            
            # Get the first file path from the list
            file_path = args.file[0]
            
            try:
                # Try full parsing (compatible with old logic)
                parsed_obj = BaseParser.parse_yaml_file(file_path)
                resource_type = parsed_obj.kind
                
                if resource_type in ("pool", "resource"):
                    if hasattr(parsed_obj, 'metadata') and hasattr(parsed_obj.metadata, 'name'):
                        resource_name = parsed_obj.metadata.name
                    elif hasattr(parsed_obj, 'pool') and hasattr(parsed_obj.pool, 'name'):
                        resource_name = parsed_obj.pool.name
                    else:
                        resource_name = file_path.replace('.yaml', '').replace('.yml', '')
                elif resource_type in JOB_KINDS:
                    # Job handling
                    if hasattr(parsed_obj, 'job') and hasattr(parsed_obj.job, 'name'):
                        resource_name = parsed_obj.job.name
                    else:
                        resource_name = file_path.replace('.yaml', '').replace('.yml', '')
                    original_resource_name = resource_name
            except Exception as e:
                # Full parsing failed, try simple YAML parsing to get necessary info
                import yaml
                with open(file_path, 'r') as f:
                    yaml_dict = yaml.safe_load(f)
                resource_type = yaml_dict['kind']
                
                if resource_type in ("pool", "resource"):
                    if 'metadata' in yaml_dict and 'name' in yaml_dict['metadata']:
                        resource_name = yaml_dict['metadata']['name']
                    elif 'pool' in yaml_dict and 'name' in yaml_dict['pool']:
                        resource_name = yaml_dict['pool']['name']
                    else:
                        resource_name = file_path.replace('.yaml', '').replace('.yml', '')
                elif resource_type in JOB_KINDS:
                    # Job handling
                    resource_name = yaml_dict['job']['name']
                    original_resource_name = resource_name
            
            if resource_type in ("pool", "resource"):
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
        
        # ── Handle job deletion ──────────────────────────────────────────
        # resource_name == YAML job.name == K8s parent resource metadata.name
        success = False

        # Determine namespaces to search
        if args.namespace:
            namespaces_to_search = [args.namespace]
        else:
            namespaces_to_search = client._get_all_gpuctl_namespaces()

        # Phase 1: Find the parent resource (Deployment/Job/StatefulSet)
        #          whose metadata.name == resource_name
        all_candidates = []  # list of (namespace, job_dict)
        for ns in namespaces_to_search:
            all_jobs = client.list_jobs(ns, labels={}, include_pods=False)
            for job in all_jobs:
                if job['name'] == resource_name:
                    all_candidates.append((ns, job))

        # Phase 2: Disambiguate across namespaces
        found_job = None
        target_ns = None

        if len(all_candidates) == 1:
            target_ns, found_job = all_candidates[0]
        elif len(all_candidates) > 1:
            msg_lines = [f"Multiple jobs named '{resource_name}' found across namespaces:"]
            for ns, j in all_candidates:
                kind = j['labels'].get(Labels.JOB_TYPE, 'unknown')
                msg_lines.append(f"  - namespace: {ns}, kind: {kind}")
            msg_lines.append("Please specify --namespace to delete a specific one.")
            if args.json:
                print(json.dumps({"error": "\n".join(msg_lines)}, indent=2))
            else:
                for line in msg_lines:
                    print(line)
            return 1

        # Phase 3: If parent resource gone, try cleaning up orphaned pods
        if not found_job:
            search_ns = namespaces_to_search
            orphan_deleted = 0
            orphan_ns = None
            for ns in search_ns:
                pods = client.list_pods(ns)
                for pod in pods:
                    pod_job_name = _get_job_name(pod.get('labels', {}))
                    if pod_job_name == resource_name:
                        try:
                            client.delete_pod(pod['name'], ns, force)
                            orphan_deleted += 1
                            orphan_ns = ns
                        except Exception:
                            pass
            if orphan_deleted > 0:
                # Also clean up any leftover service
                try:
                    client.delete_service(svc_name(resource_name), orphan_ns)
                except Exception:
                    pass
                msg = f"Deleted {orphan_deleted} orphaned pod(s) for job: {original_resource_name}"
                if args.json:
                    print(json.dumps({"status": "success", "message": msg}, indent=2))
                else:
                    print(f"✅ {msg}")
                return 0

        # Phase 4: Execute deletion of parent resource + service
        if found_job:
            actual_job_type = found_job['labels'].get(Labels.JOB_TYPE, 'unknown')
            actual_job_name = found_job['name']
            ns = target_ns

            if actual_job_type == Kind.TRAINING:
                success = client.delete_job(actual_job_name, ns, force)
            elif actual_job_type in (Kind.INFERENCE, Kind.COMPUTE):
                deployment_deleted = client.delete_deployment(actual_job_name, ns, force)
                service_deleted = client.delete_service(svc_name(actual_job_name), ns)
                success = deployment_deleted and service_deleted
            elif actual_job_type == Kind.NOTEBOOK:
                statefulset_deleted = client.delete_statefulset(actual_job_name, ns, force)
                service_deleted = client.delete_service(svc_name(actual_job_name), ns)
                success = statefulset_deleted and service_deleted

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
        
        # Check if there are multiple jobs with the same name in different namespaces
        # Get all gpuctl-managed namespaces
        gpuctl_namespaces = client._get_all_gpuctl_namespaces()

        # Helper function to check if input looks like a Pod name
        def is_pod_name_input(input_name):
            """Check if input name looks like a Pod name"""
            parts = input_name.split('-')
            if len(parts) < 3:
                return False
            # Check for StatefulSet Pod: ends with digit (e.g., "name-0")
            if parts[-1].isdigit():
                return True
            # Check for Deployment/Job Pod: contains hash-like part (8-10 alphanumeric chars)
            for i, part in enumerate(parts[2:], 2):
                if len(part) >= 8 and part.isalnum():
                    return True
            return False

        # Collect all matching jobs
        matching_jobs = []

        # First, try to match controller resources (Deployment/StatefulSet/Job) only
        # Skip Pod matching if user input doesn't look like a Pod name
        user_input_is_pod = is_pod_name_input(args.job_id)

        for ns in gpuctl_namespaces:
            # Get controller resources only (exclude Pods)
            controller_jobs = client.list_jobs(ns, include_pods=False)
            for job_item in controller_jobs:
                job_name = job_item['name']
                # Check if matches full name or original name (without prefix)
                if job_name == args.job_id or remove_prefix(job_name) == args.job_id:
                    matching_jobs.append(job_item)
                else:
                    # Check if job name starts with user input (fuzzy match)
                    # e.g., user input "new-test" matches "new-test-notebook-job"
                    if job_name.startswith(args.job_id) or remove_prefix(job_name).startswith(args.job_id):
                        matching_jobs.append(job_item)

        # If no controller resources matched and user input looks like a Pod name,
        # then try to match Pod resources
        if not matching_jobs and user_input_is_pod:
            for ns in gpuctl_namespaces:
                # Get all jobs including Pod instances
                all_jobs = client.list_jobs(ns, include_pods=True)
                for job_item in all_jobs:
                    job_name = job_item['name']
                    # Check if matches full name or original name (without prefix)
                    if job_name == args.job_id or remove_prefix(job_name) == args.job_id:
                        matching_jobs.append(job_item)
                    else:
                        # Check if it's a full pod name with hash suffix
                        # Format: base-name-deployment-hash-pod-suffix -> extract base-name
                        parts = job_name.split("-")
                        if len(parts) >= 3:
                            third_part = parts[2] if len(parts) >= 3 else ''
                            if third_part.isalnum() and len(third_part) >= 5:
                                # This is likely a full pod name, extract base name
                                base_job_name = '-'.join(parts[:2])
                                if base_job_name == args.job_id or remove_prefix(base_job_name) == args.job_id:
                                    matching_jobs.append(job_item)
        
        # Check if there are multiple matching jobs from different namespaces
        # Extract unique namespaces from matching jobs
        unique_namespaces = set()
        for job_item in matching_jobs:
            namespace = job_item.get('namespace', 'default')
            unique_namespaces.add(namespace)
        
        # Collected unique namespaces for multi-namespace disambiguation
        
        # Check if there are multiple matching jobs from different namespaces
        if len(unique_namespaces) > 1:
            # Check if namespace is specified
            if args.namespace:
                # Namespace is specified, filter jobs by namespace
                filtered_jobs = [j for j in matching_jobs if j.get('namespace') == args.namespace]
                if len(filtered_jobs) == 1:
                    job = filtered_jobs[0]
                elif len(filtered_jobs) > 1:
                    # Multiple jobs in the same namespace, this should not happen
                    if args.json:
                        import json
                        print(json.dumps({"error": "Multiple jobs with the same name found in the specified namespace."}, indent=2))
                    else:
                        print("❌ Multiple jobs with the same name found in the specified namespace.")
                    return 1
                else:
                    # No jobs in the specified namespace
                    job = None
            else:
                # Multiple jobs with the same name found in different namespaces, need to specify namespace
                if args.json:
                    import json
                    print(json.dumps({"error": "Multiple jobs with the same name found in different namespaces. Please specify namespace."}, indent=2))
                else:
                    print("❌ Multiple jobs with the same name found in different namespaces. Please specify namespace.")
                return 1
        elif len(matching_jobs) == 1:
            # Only one matching job found
            job = matching_jobs[0]
        else:
            # No matching jobs found
            job = None
        
        if not job:
            # If still not found, try direct lookup in specified namespace
            job = client.get_job(args.job_id, args.namespace)
            
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
                            job_types = list(JOB_KINDS)
                            found = False
                            for job_type in job_types:
                                prefixed_job_id = add_prefix(base_job_name, job_type)
                                job = client.get_job(prefixed_job_id, args.namespace)
                                if job:
                                    found = True
                                    break
                            
                            if not found:
                                # Get all jobs including Pod instances to query actual job
                                all_jobs = client.list_jobs(args.namespace, include_pods=True)
                                # Also check all_jobs for base name match
                                found_job = None
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
                "namespace": job.get('namespace', DEFAULT_NAMESPACE),
                "kind": job.get('labels', {}).get(Labels.JOB_TYPE, 'unknown'),
                "status": "Unknown",
                "age": calculate_age(job.get('creation_timestamp')),
                "started": job.get('start_time', 'N/A'),
                "completed": job.get('completion_time', 'N/A'),
                "priority": job.get('labels', {}).get(Labels.PRIORITY, DEFAULT_PRIORITY),
                "pool": job.get('labels', {}).get(Labels.POOL, DEFAULT_POOL),
                "resources": job.get('resources', {}),
                "metrics": job.get('metrics', {})
            }
            
            job_type = job.get('labels', {}).get(Labels.JOB_TYPE, 'unknown')
            status_dict = job.get('status', {})
            pods = job.get('pods', [])
            
            status = "Unknown"
            
            if "phase" in status_dict:
                pod_phase = status_dict.get("phase", "Unknown")
                status = PHASE_TO_STATUS.get(pod_phase, pod_phase)
                
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

            # ── resource_type ──────────────────────────────────────────────
            rt = infer_resource_type(status_dict, job_type)
            processed_job['resource_type'] = rt

            # ── yaml_content ───────────────────────────────────────────────
            try:
                from gpuctl.cli.job_mapper import map_k8s_to_gpuctl
                processed_job['yaml_content'] = map_k8s_to_gpuctl(job)
            except Exception:
                processed_job['yaml_content'] = {}

            # ── events ─────────────────────────────────────────────────────
            full_job_name = job.get('name', '')
            actual_namespace = job.get('namespace', args.namespace)
            events_list = []
            try:
                from gpuctl.client.base_client import KubernetesClient
                _k8s = KubernetesClient()
                _evs = _k8s.core_v1.list_namespaced_event(
                    namespace=actual_namespace,
                    field_selector=f"involvedObject.name={full_job_name},involvedObject.kind={rt}",
                    limit=10
                )
                _sorted = sorted(
                    _evs.items,
                    key=lambda e: e.last_timestamp or e.first_timestamp or e.event_time or '',
                    reverse=True
                )[:10]
                for _ev in _sorted:
                    _ts = _ev.last_timestamp or _ev.first_timestamp or _ev.event_time
                    _ts_str = None
                    if _ts:
                        _ts_str = _ts.isoformat()
                        if '.' in _ts_str:
                            _ts_str = _ts_str.split('.')[0] + 'Z'
                    events_list.append({
                        "age": _format_event_age(_ts_str),
                        "type": _ev.type or 'Normal',
                        "reason": _ev.reason or '-',
                        "from": _ev.source.component if _ev.source and _ev.source.component else '-',
                        "object": f"{_ev.involved_object.kind}/{_ev.involved_object.name}",
                        "message": _ev.message or '-'
                    })
            except Exception:
                pass
            processed_job['events'] = events_list

            # ── access_methods (inference / compute / notebook only) ────────
            if job_type in KINDS_WITH_SERVICE:
                _access = {}
                # 计算服务名
                _svc_base = remove_prefix(full_job_name)
                if job_type == Kind.NOTEBOOK:
                    _parts = _svc_base.split('-')
                    if len(_parts) >= 2 and _parts[-1].isdigit():
                        _svc_base = '-'.join(_parts[:-1])
                elif rt == K8sResourceType.POD:
                    _parts = _svc_base.split('-')
                    if len(_parts) >= 3 and _parts[2].isalnum() and len(_parts[2]) >= 5:
                        _svc_base = '-'.join(_parts[:2])

                _target_port = None
                _service_port = None
                _node_port = None
                try:
                    from gpuctl.client.base_client import KubernetesClient
                    _k8s2 = KubernetesClient()
                    _svc = _k8s2.core_v1.read_namespaced_service(
                        name=svc_name(_svc_base), namespace=actual_namespace
                    ).to_dict()
                    if _svc['spec']['ports']:
                        _p = _svc['spec']['ports'][0]
                        _target_port = _p.get('target_port')
                        _service_port = _p.get('port')
                        _node_port = _p.get('node_port')
                except Exception:
                    pass

                # 获取 Node IP
                _node_ip = None
                try:
                    from gpuctl.client.base_client import KubernetesClient
                    _k8s3 = KubernetesClient()
                    _nodes = _k8s3.core_v1.list_node().items
                    if _nodes:
                        for _addr in (_nodes[0].to_dict().get('status', {}).get('addresses', [])):
                            if _addr.get('type') == 'InternalIP':
                                _node_ip = _addr.get('address')
                                break
                except Exception:
                    pass

                # 获取 Pod IP
                _pod_ip = None
                _is_running = False
                try:
                    from gpuctl.client.base_client import KubernetesClient
                    _k8s4 = KubernetesClient()
                    if rt == K8sResourceType.POD:
                        _pod = _k8s4.core_v1.read_namespaced_pod(
                            name=full_job_name, namespace=actual_namespace
                        )
                        _is_running = _pod.status.phase == 'Running'
                        _pod_ip = _pod.status.pod_ip
                    else:
                        _pods = _k8s4.core_v1.list_namespaced_pod(
                            namespace=actual_namespace,
                            label_selector=f"{Labels.APP}={full_job_name}"
                        )
                        for _p2 in _pods.items:
                            if _p2.status.phase == 'Running':
                                _is_running = True
                                _pod_ip = _p2.status.pod_ip
                                break
                except Exception:
                    pass

                _port = _target_port or _service_port
                _access['pod_ip_access'] = {
                    "pod_ip": _pod_ip if _is_running else None,
                    "port": _port,
                    "url": f"http://{_pod_ip}:{_port}" if (_is_running and _pod_ip and _port) else None
                }
                _access['node_port_access'] = {
                    "node_ip": _node_ip,
                    "node_port": _node_port,
                    "url": f"http://{_node_ip}:{_node_port}" if (_node_ip and _node_port) else None
                }
                processed_job['access_methods'] = _access

            print(json.dumps(processed_job, indent=2))
            return 0
        
        # 输出文本格式
        # Print job details with prefix removed
        display_name = remove_prefix(job.get('name', 'N/A'))
        print(f"📋 Job Details: {display_name}")
        print(f"📊 Name: {display_name}")
        
        job_type = job.get('labels', {}).get(Labels.JOB_TYPE, 'unknown')
        status_dict = job.get('status', {})
        
        resource_type = infer_resource_type(status_dict, job_type)
        
        if resource_type == K8sResourceType.POD:
            pod_phase = status_dict.get("phase", "Unknown")
            status = PHASE_TO_STATUS.get(pod_phase, pod_phase)
        elif resource_type == K8sResourceType.DEPLOYMENT:
            ready_replicas = status_dict.get("ready_replicas", 0)
            unavailable_replicas = status_dict.get("unavailable_replicas", 0)
            total_replicas = ready_replicas + unavailable_replicas
            
            if total_replicas == 0:
                status = "Pending"
            elif ready_replicas > 0 and unavailable_replicas == 0:
                status = "Running"
            elif ready_replicas > 0:
                status = "Partially Running"
            else:
                status = "Pending"
        elif resource_type == K8sResourceType.JOB:
            active = status_dict.get("active", 0)
            succeeded = status_dict.get("succeeded", 0)
            failed = status_dict.get("failed", 0)
            
            if active > 0:
                status = "Running"
            elif succeeded > 0:
                status = "Succeeded"
            elif failed > 0:
                status = "Failed"
            else:
                status = "Pending"
        elif resource_type == K8sResourceType.STATEFULSET:
            ready_replicas = status_dict.get("readyReplicas", 0)
            total_replicas = status_dict.get("currentReplicas", ready_replicas)
            
            if total_replicas == 0:
                status = "Pending"
            elif ready_replicas > 0 and ready_replicas >= total_replicas:
                status = "Running"
            elif ready_replicas > 0:
                status = "Partially Running"
            else:
                status = "Pending"
        else:
            status = "Unknown"
        
        # Calculate AGE
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
        print(f"📁 Resource Type: {resource_type}")
        print(f"📈 Status: {status}")
        print(f"⏰ Age: {age}")
        print(f"🔧 Started: {job.get('start_time', 'N/A')}")
        print(f"🏁 Completed: {job.get('completion_time', 'N/A')}")
        print(f"📋 Priority: {job.get('labels', {}).get(Labels.PRIORITY, DEFAULT_PRIORITY)}")
        print(f"🖥️  Pool: {job.get('labels', {}).get(Labels.POOL, DEFAULT_POOL)}")
        
        if resource_type == K8sResourceType.DEPLOYMENT:
            print("\n📦 Deployment Status:")
            print(f"   Ready Replicas: {status_dict.get('ready_replicas', 0)}")
            print(f"   Unavailable Replicas: {status_dict.get('unavailable_replicas', 0)}")
            print(f"   Current Replicas: {status_dict.get('current_replicas', 0)}")
            print(f"   Desired Replicas: {status_dict.get('replicas', 0)}")
        
        # Display original YAML key content
        print("\n📝 Original YAML Key Content:")
        # Import the job mapper function
        from gpuctl.cli.job_mapper import get_original_yaml_content
        # Generate the mapped YAML content
        yaml_content = get_original_yaml_content(job)
        # Print the YAML content with proper indentation
        for line in yaml_content.strip().split('\n'):
            print(f"   {line}")
        
        full_job_name = job.get('name', '')
        if full_job_name:
            try:
                # Create Kubernetes client to get events
                from gpuctl.client.base_client import KubernetesClient
                k8s_client = KubernetesClient()

                # Get actual namespace from job or use args.namespace
                actual_namespace = job.get('namespace', args.namespace)

                all_events = []

                # Query events based on resource_type
                # resource_type is now correctly determined by the matching logic above
                field_selector = f"involvedObject.name={full_job_name},involvedObject.kind={resource_type}"
                try:
                    events = k8s_client.core_v1.list_namespaced_event(
                        namespace=actual_namespace,
                        field_selector=field_selector,
                        limit=10
                    )
                    all_events.extend(events.items)
                except Exception:
                    pass
                
                # Sort events by timestamp (newest first)
                all_events.sort(key=lambda e: e.last_timestamp or e.first_timestamp or e.event_time or '', reverse=True)
                
                # Limit to 10 events
                all_events = all_events[:10]
                
                if all_events:
                    print(f"\n📋 Events:")
                    
                    for i, event in enumerate(all_events):
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
                        involved_object = f"{event.involved_object.kind}/{event.involved_object.name}"
                        
                        print(f"  [{age}] {event_type} {reason}")
                        print(f"    From: {source}")
                        print(f"    Object: {involved_object}")
                        print(f"    Message: {message}")
                        
                        if i < len(all_events) - 1:
                            print()
            except Exception as e:
                print(f"\n⚠️  Failed to get events: {e}")
        
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
        
        job_type = job.get('labels', {}).get(Labels.JOB_TYPE, '')
        if job_type in KINDS_WITH_SERVICE:
            print("\n🌐 Access Methods:")
            
            # Get full job name and actual namespace from the job
            full_job_name = job.get('name', '')
            actual_namespace = job.get('namespace', args.namespace)
            
            # Extract base job name
            base_job_name = remove_prefix(full_job_name)
            
            # Extract service base name
            service_base_name = base_job_name

            # Handle different job types for service name extraction
            if job_type == Kind.NOTEBOOK:
                parts = service_base_name.split('-')
                if len(parts) >= 2 and parts[-1].isdigit():
                    service_base_name = '-'.join(parts[:-1])
            elif resource_type == K8sResourceType.POD:
                # Deployment Pod format: base-name-deployment-hash-pod-suffix
                parts = base_job_name.split('-')
                if len(parts) >= 3:
                    third_part = parts[2] if len(parts) >= 3 else ''
                    if third_part.isalnum() and len(third_part) >= 5:
                        # This is likely a full pod name, extract base name
                        service_base_name = '-'.join(parts[:2])
            
            # Get Service info first to get ports
            service_data = None
            service_found = True
            try:
                # Create Kubernetes client to get service
                from gpuctl.client.base_client import KubernetesClient
                k8s_client = KubernetesClient()
                
                # Get Service using actual namespace
                service = k8s_client.core_v1.read_namespaced_service(
                    name=svc_name(service_base_name),
                    namespace=actual_namespace
                )
                service_data = service.to_dict()
            except Exception as e:
                service_found = False
            
            # Get Node IP first (needed for both methods)
            node_ip = 'N/A'
            try:
                from gpuctl.client.base_client import KubernetesClient
                k8s_client = KubernetesClient()
                nodes = k8s_client.core_v1.list_node()
                node_items = nodes.items
                if node_items:
                    node_dict = node_items[0].to_dict()
                    node_addresses = node_dict.get('status', {}).get('addresses', [])
                    for addr in node_addresses:
                        if addr.get('type') == 'InternalIP':
                            node_ip = addr.get('address')
                            break
            except Exception:
                pass

            # Get port info from service
            target_port = 'N/A'
            service_port = 'N/A'
            node_port = 'N/A'
            if service_found and service_data:
                target_port = service_data['spec']['ports'][0].get('target_port', 'N/A') if service_data['spec']['ports'] else 'N/A'
                service_port = service_data['spec']['ports'][0].get('port', 'N/A') if service_data['spec']['ports'] else 'N/A'
                node_port = service_data['spec']['ports'][0].get('node_port', 'N/A') if service_data['spec']['ports'] else 'N/A'

            # Check if pod is running
            is_running = False
            pod_status = 'Unknown'
            pod_ip = 'N/A'
            try:
                from gpuctl.client.base_client import KubernetesClient
                k8s_client = KubernetesClient()
                if resource_type == K8sResourceType.POD:
                    pod = k8s_client.core_v1.read_namespaced_pod(
                        name=full_job_name,
                        namespace=actual_namespace
                    )
                    pod_status = pod.status.phase or 'Unknown'
                    is_running = pod_status == 'Running'
                    pod_ip = pod.status.pod_ip or 'N/A'
                else:
                    pods = k8s_client.core_v1.list_namespaced_pod(
                        namespace=actual_namespace,
                        label_selector=f"{Labels.APP}={full_job_name}"
                    )
                    for pod in pods.items:
                        if pod.status.phase == 'Running':
                            is_running = True
                            pod_ip = pod.status.pod_ip or 'N/A'
                            break
            except Exception:
                pass

            # Method 1: Access via Pod IP
            print(f"   1. Pod IP Access:")
            if is_running and pod_ip != 'N/A':
                pod_port = target_port if target_port != 'N/A' else service_port
                print(f"      - Pod IP: {pod_ip}")
                print(f"      - Port: {pod_port}")
                print(f"      - Access: curl http://{pod_ip}:{pod_port}")
            else:
                # Pod is not running, show initializing message like create command
                expected_port = target_port if target_port != 'N/A' else service_port
                print(f"      - Pod is initializing, IP will be available once running")
                if expected_port != 'N/A':
                    print(f"      - Expected Port: {expected_port}")

            # Method 2: Access via NodePort
            print(f"   2. NodePort Access:")
            if not service_found:
                # Service not found, show friendly message
                print(f"      - Service not available for this job")
            else:
                if node_ip != 'N/A':
                    print(f"      - Node IP: {node_ip}")
                if node_port != 'N/A':
                    print(f"      - NodePort: {node_port}")
                if is_running and node_ip != 'N/A' and node_port != 'N/A':
                    print(f"      - Access: curl http://{node_ip}:{node_port}")
        
        return 0
    except Exception as e:
        if args.json:
            import json
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"❌ Error describing job: {e}")
        return 1
