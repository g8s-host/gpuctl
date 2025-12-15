from gpuctl.client.pool_client import PoolClient


def get_nodes_command(args):
    """获取节点列表命令"""
    try:
        client = PoolClient()
        
        # 构建过滤条件
        filters = {}
        if args.pool:
            filters["pool"] = args.pool
        if args.gpu_type:
            filters["gpu_type"] = args.gpu_type
        
        # 调用API获取节点列表，传递过滤条件
        nodes = client.list_nodes(filters=filters)
        
        # 打印节点列表
        print(f"{'NODE NAME':<30} {'STATUS':<10} {'GPU TOTAL':<10} {'GPU USED':<10} {'GPU FREE':<10} {'GPU TYPE':<15} {'POOL':<20}")
        
        for node in nodes:
            # 安全访问字典字段，使用默认值处理缺失情况
            name = node.get('name', 'N/A')
            status = node.get('status', 'unknown')
            gpu_total = node.get('gpu_total', 0)
            gpu_used = node.get('gpu_used', 0)
            gpu_free = node.get('gpu_free', 0)
            gpu_types = ', '.join(node.get('gpu_types', []))
            pool = node.get('labels', {}).get('g8s.host/pool', 'default')
            
            print(f"{name:<30} {status:<10} {gpu_total:<10} {gpu_used:<10} {gpu_free:<10} {gpu_types:<15} {pool:<20}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting nodes: {e}")
        return 1


def get_labels_command(args):
    """获取节点标签命令"""
    try:
        client = PoolClient()
        
        # 获取节点信息
        node = client.get_node(args.node_name)
        
        # 获取节点标签
        labels = node.get('labels', {})
        
        # 如果指定了key，则只打印该key的标签
        if args.key:
            if args.key in labels:
                print(f"{args.node_name} {args.key}: {labels[args.key]}")
            else:
                print(f"❌ Label {args.key} not found on node {args.node_name}")
        else:
            # 打印所有标签
            print(f"🏷️  Labels for node {args.node_name}:")
            for key, value in labels.items():
                print(f"   {key}: {value}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting labels: {e}")
        return 1


def label_node_command(args):
    """为节点添加标签命令"""
    try:
        client = PoolClient()
        
        for node_name in args.node_name:
            if args.delete:
                # 删除标签
                if args.label:
                    key = args.label.split('=')[0]
                    client._remove_node_label(node_name, key)
                    print(f"✅ Successfully removed label {key} from node {node_name}")
                else:
                    print(f"❌ Must specify label to delete")
                    return 1
            else:
                # 添加或更新标签
                if args.label:
                    key, value = args.label.split('=')
                    client._label_node(node_name, key, value)
                    print(f"✅ Successfully labeled node {node_name} with {key}={value}")
                else:
                    print(f"❌ Must specify label in key=value format")
                    return 1
        
        return 0
    except Exception as e:
        print(f"❌ Error labeling node: {e}")
        return 1


def add_node_to_pool_command(args):
    """将节点添加到资源池命令"""
    try:
        client = PoolClient()
        result = client.add_nodes_to_pool(args.pool, args.node_name)
        
        if result['success']:
            print(f"✅ Successfully added nodes {', '.join(result['success'])} to pool {args.pool}")
        
        if result['failed']:
            for failure in result['failed']:
                print(f"❌ Failed to add node {failure['node']}: {failure['error']}")
        
        return 0
    except Exception as e:
        print(f"❌ Error adding node to pool: {e}")
        return 1


def remove_node_from_pool_command(args):
    """从资源池移除节点命令"""
    try:
        client = PoolClient()
        result = client.remove_nodes_from_pool(args.pool, args.node_name)
        
        if result['success']:
            print(f"✅ Successfully removed nodes {', '.join(result['success'])} from pool {args.pool}")
        
        if result['failed']:
            for failure in result['failed']:
                print(f"❌ Failed to remove node {failure['node']}: {failure['error']}")
        
        return 0
    except Exception as e:
        print(f"❌ Error removing node from pool: {e}")
        return 1


def describe_node_command(args):
    """描述节点详情命令"""
    try:
        client = PoolClient()
        node = client.get_node(args.node_name)
        
        # 打印节点详情
        print(f"📋 Node Details: {args.node_name}")
        print(f"📊 Name: {node.get('name', 'N/A')}")
        print(f"📈 Status: {node.get('status', 'unknown')}")
        print(f"🔧 K8s Status: {node.get('k8s_status', 'N/A')}")
        print(f"🖥️  Pool: {node.get('labels', {}).get('g8s.host/pool', 'default')}")
        print(f"⏰ Created: {node.get('created_at', 'N/A')}")
        print(f"⏰ Last Updated: {node.get('last_updated_at', 'N/A')}")
        
        if 'resources' in node:
            print("\n💻 Resources:")
            resources = node['resources']
            print(f"   CPU Total: {resources.get('cpu_total', 'N/A')}")
            print(f"   CPU Used: {resources.get('cpu_used', 'N/A')}")
            print(f"   Memory Total: {resources.get('memory_total', 'N/A')}")
            print(f"   Memory Used: {resources.get('memory_used', 'N/A')}")
            print(f"   GPU Total: {resources.get('gpu_total', 'N/A')}")
            print(f"   GPU Used: {resources.get('gpu_used', 'N/A')}")
            print(f"   GPU Free: {resources.get('gpu_free', 'N/A')}")
        
        if 'gpu_detail' in node:
            print("\n🖥️  GPU Details:")
            for gpu in node['gpu_detail']:
                print(f"   GPU {gpu.get('gpuId', 'N/A')}:")
                print(f"      Type: {gpu.get('type', 'N/A')}")
                print(f"      Status: {gpu.get('status', 'N/A')}")
                print(f"      Utilization: {gpu.get('utilization', 'N/A')}%")
                print(f"      Memory Usage: {gpu.get('memoryUsage', 'N/A')}")
        
        if 'labels' in node:
            print("\n🏷️  Labels:")
            for key, value in node['labels'].items():
                print(f"   {key}: {value}")
        
        if 'running_jobs' in node:
            print("\n📋 Running Jobs:")
            for job in node['running_jobs']:
                print(f"   - {job.get('name', 'N/A')} (GPU: {job.get('gpu', 0)})")
        
        return 0
    except Exception as e:
        print(f"❌ Error describing node: {e}")
        return 1
