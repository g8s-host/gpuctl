from gpuctl.client.pool_client import PoolClient


def get_nodes_command(args):
    """获取节点列表命令"""
    try:
        client = PoolClient()
        nodes = client.list_nodes()
        
        # 打印节点列表
        print(f"{'NODE NAME':<30} {'STATUS':<10} {'GPU TOTAL':<10} {'GPU USED':<10} {'GPU FREE':<10} {'GPU TYPE':<15} {'POOL':<20}")
        print("-" * 120)
        
        for node in nodes:
            print(f"{node['name']:<30} {node['status']:<10} {node['gpu_total']:<10} {node['gpu_used']:<10} {node['gpu_free']:<10} {', '.join(node['gpu_types']):<15} {node['labels'].get('gpuctl/pool', 'default'):<20}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting nodes: {e}")
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
