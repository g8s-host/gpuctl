#!/usr/bin/env python3
"""
gpuctl自动化测试脚本
用于一键测试gpuctl代码在真实K8s环境中的运行情况
"""

import os
import sys
import logging
import argparse
import subprocess
import time
import shutil
from datetime import datetime
from dotenv import load_dotenv

# 设置日志
LOG_DIR = os.path.join("tests", "test_logs")
LOG_FILE = os.path.join(LOG_DIR, f"test_gpuctl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# 配置根日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("test_gpuctl")


def load_config():
    """加载配置文件"""
    logger.info("开始加载配置文件")
    
    # 尝试从tests目录加载.env文件
    env_path = os.path.join("tests", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"配置文件 {env_path} 加载成功")
    else:
        # 尝试从当前目录加载.env文件（向后兼容）
        current_env_path = ".env"
        if os.path.exists(current_env_path):
            load_dotenv(current_env_path)
            logger.info(f"配置文件 {current_env_path} 加载成功")
        else:
            logger.info("配置文件 .env 不存在，将使用默认配置（本地K8s集群）")
    
    # 获取配置项，所有配置项都是可选的，默认使用本地K8s环境
    config = {
        "k8s_master_ip": os.getenv("K8S_MASTER_IP"),
        "k8s_api_port": os.getenv("K8S_API_PORT", "6443"),
        "k8s_token": os.getenv("K8S_TOKEN"),
        "k8s_ca_cert": os.getenv("K8S_CA_CERT"),
        "log_level": os.getenv("LOG_LEVEL", "DEBUG"),
        "api_host": os.getenv("API_HOST", "0.0.0.0"),
        "api_port": os.getenv("API_PORT", "8000"),
        "default_namespace": os.getenv("DEFAULT_NAMESPACE")
    }
    
    logger.info(f"加载的配置信息: {config}")
    return config


def run_command(cmd, cwd=None, env=None):
    """运行命令并返回结果"""
    logger.debug(f"执行命令: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=env
        )
        logger.debug(f"命令执行成功: {cmd}")
        logger.debug(f"命令输出: {result.stdout}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"命令执行失败: {cmd}")
        logger.error(f"错误码: {e.returncode}")
        logger.error(f"标准输出: {e.stdout}")
        logger.error(f"错误输出: {e.stderr}")
        return False, e.stderr


def setup_kubeconfig(config):
    """设置kubeconfig文件"""
    # 如果没有提供K8s master IP，使用本地kubeconfig文件
    if not config['k8s_master_ip']:
        logger.info("未提供K8s master IP，将使用本地kubeconfig文件")
        return None
    
    logger.info("开始设置kubeconfig文件")
    
    kubeconfig_content = f"""
apiVersion: v1
clusters:
- cluster:
    server: https://{config['k8s_master_ip']}:{config['k8s_api_port']}
    {f'certificate-authority: {config['k8s_ca_cert']}' if config['k8s_ca_cert'] else 'insecure-skip-tls-verify: true'}
  name: test-cluster
contexts:
- context:
    cluster: test-cluster
    user: test-user
  name: test-context
current-context: test-context
kind: Config
preferences: {{}}
users:
- name: test-user
  user:
    {f'token: {config['k8s_token']}' if config['k8s_token'] else ''}
"""
    
    # 保存kubeconfig文件
    kubeconfig_path = os.path.join(os.getcwd(), "test_kubeconfig")
    with open(kubeconfig_path, "w") as f:
        f.write(kubeconfig_content)
    
    logger.info(f"kubeconfig文件已保存到: {kubeconfig_path}")
    return kubeconfig_path


def test_unit_tests():
    """运行单元测试"""
    logger.info("开始运行单元测试")
    
    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["LOG_LEVEL"] = "DEBUG"
    
    # 运行pytest
    success, output = run_command(
        "poetry run pytest -v",
        env=env
    )
    
    if success:
        logger.info("单元测试全部通过")
    else:
        logger.error("单元测试失败")
    
    return success


def test_cli_commands(kubeconfig_path):
    """测试CLI命令"""
    logger.info("开始测试CLI命令")
    
    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["LOG_LEVEL"] = "DEBUG"
    
    # 只有当提供了kubeconfig_path时才设置KUBECONFIG环境变量
    if kubeconfig_path:
        env["KUBECONFIG"] = kubeconfig_path
        logger.info(f"使用kubeconfig文件: {kubeconfig_path}")
    else:
        logger.info("使用本地kubeconfig文件")
    
    # 测试命令列表
    test_commands = [
        "poetry run gpuctl get nodes",
        "poetry run gpuctl get pools",
    ]
    
    results = []
    for cmd in test_commands:
        logger.info(f"测试命令: {cmd}")
        success, output = run_command(cmd, env=env)
        results.append((cmd, success))
    
    # 统计结果
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info(f"CLI命令测试完成: {passed}/{total} 命令通过")
    
    return passed == total


def test_api_endpoints(config):
    """测试API端点"""
    logger.info("开始测试API端点")
    
    api_url = f"http://{config['api_host']}:{config['api_port']}"
    
    # 测试命令列表
    test_commands = [
        f"curl -s {api_url}/",
        f"curl -s {api_url}/health",
    ]
    
    results = []
    for cmd in test_commands:
        logger.info(f"测试API端点: {cmd}")
        success, output = run_command(cmd)
        results.append((cmd, success))
    
    # 统计结果
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info(f"API端点测试完成: {passed}/{total} 端点通过")
    
    return passed == total


def start_api_server(config, kubeconfig_path):
    """启动API服务器"""
    logger.info("开始启动API服务器")
    
    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["LOG_LEVEL"] = "DEBUG"
    
    # 只有当提供了kubeconfig_path时才设置KUBECONFIG环境变量
    if kubeconfig_path:
        env["KUBECONFIG"] = kubeconfig_path
        logger.info(f"使用kubeconfig文件: {kubeconfig_path}")
    else:
        logger.info("使用本地kubeconfig文件")
    
    # 启动API服务器（非阻塞）
    process = subprocess.Popen(
        f"poetry run python server/main.py",
        shell=True,
        cwd=os.getcwd(),
        env=env
    )
    
    # 等待服务器启动
    time.sleep(3)
    
    # 检查服务器是否启动成功
    success, _ = run_command(f"curl -s {config['api_host']}:{config['api_port']}/health")
    if success:
        logger.info(f"API服务器启动成功，访问地址: http://{config['api_host']}:{config['api_port']}")
        return process
    else:
        logger.error("API服务器启动失败")
        process.kill()
        return None


def main():
    """主函数"""
    logger.info("="*60)
    logger.info("gpuctl自动化测试脚本启动")
    logger.info(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    try:
        # 1. 加载配置
        config = load_config()
        logger.info(f"配置信息: {config}")
        
        # 2. 设置kubeconfig
        kubeconfig_path = setup_kubeconfig(config)
        
        # 3. 运行单元测试
        logger.info("="*60)
        unit_test_result = test_unit_tests()
        
        # 4. 启动API服务器
        logger.info("="*60)
        api_server = start_api_server(config, kubeconfig_path)
        
        try:
            # 5. 测试API端点
            logger.info("="*60)
            api_test_result = test_api_endpoints(config) if api_server else False
            
            # 6. 测试CLI命令
            logger.info("="*60)
            cli_test_result = test_cli_commands(kubeconfig_path)
        finally:
            # 停止API服务器
            if api_server:
                logger.info("停止API服务器")
                api_server.kill()
                api_server.wait()
        
        # 7. 清理kubeconfig文件
        if kubeconfig_path and os.path.exists(kubeconfig_path):
            os.remove(kubeconfig_path)
            logger.info(f"清理kubeconfig文件: {kubeconfig_path}")
        
        # 8. 总结测试结果
        logger.info("="*60)
        logger.info("自动化测试完成")
        logger.info(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        logger.info(f"单元测试结果: {'通过' if unit_test_result else '失败'}")
        logger.info(f"API端点测试结果: {'通过' if api_test_result else '失败'}")
        logger.info(f"CLI命令测试结果: {'通过' if cli_test_result else '失败'}")
        
        all_passed = unit_test_result and api_test_result and cli_test_result
        logger.info(f"总体测试结果: {'全部通过' if all_passed else '存在失败'}")
        
        logger.info(f"测试日志已保存到: {LOG_FILE}")
        
        if all_passed:
            logger.info("🎉 恭喜！所有测试都通过了！")
            sys.exit(0)
        else:
            logger.error("❌ 测试失败，请查看日志了解详情")
            sys.exit(1)
            
    except Exception as e:
        logger.exception(f"自动化测试脚本执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
