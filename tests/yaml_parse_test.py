from gpuctl.parser.base_parser import BaseParser

# 测试YAML内容
test_yaml = """
kind: training 
version: v0.1 

# 任务标识与描述（Llama Factory微调场景） 
job: 
  name: qwen2-7b-llamafactory-sft 
  description: llama3推理任务 


# 环境与镜像 - 集成Llama Factory 0.8.0 + DeepSpeed 0.14.0 
environment: 
  image: registry.example.com/llama-factory-deepspeed:v0.8.0 
  imagePullSecret: my-secret 
  # Llama Factory微调核心命令 
  command: ["llama-factory-cli", "train", "--stage", "sft", "--model_name_or_path", "/models/qwen2-7b", "--dataset", "alpaca-qwen", "--dataset_dir", "/datasets", "--output_dir", "/output/qwen2-sft", "--per_device_train_batch_size", "8", "--gradient_accumulation_steps", "4", "--learning_rate", "2e-5", "--deepspeed", "ds_config.json"] 
  env: 
    - name: NVIDIA_FLASH_ATTENTION 
      value: "1" 
    - name: LLAMA_FACTORY_CACHE 
      value: "/cache/llama-factory" 

# 资源需求声明（4卡A100） 
resources: 
  pool: training-pool 
  gpu: 4 
  cpu: 32 
  memory: 128Gi 
  gpu_share: 2Gi 


# 数据与模型配置 
storage: 
  workdirs: 
    - path: /datasets/alpaca-qwen.json 
    - path: /models/qwen2-7b    
    - path: /cache/models 
    - path: /output/qwen2-sft 
    - path: /output/qwen2-sft/checkpoints
"""

def test_yaml_parsing():
    try:
        # 解析YAML
        parsed_obj = BaseParser.parse_yaml(test_yaml)
        print("YAML解析成功！")
        print(f"解析对象类型: {type(parsed_obj)}")
        print(f"任务类型: {parsed_obj.kind}")
        print(f"任务名称: {parsed_obj.job.name}")
        print(f"GPU数量: {parsed_obj.resources.gpu}")
        print(f"CPU需求: {parsed_obj.resources.cpu}")
        print(f"内存需求: {parsed_obj.resources.memory}")
        print(f"训练轮次: {parsed_obj.job.epochs}")
        print(f"批次大小: {parsed_obj.job.batch_size}")
        print(f"镜像地址: {parsed_obj.environment.image}")
        print(f"命令: {parsed_obj.environment.command}")
        return True
    except Exception as e:
        print(f"YAML解析失败: {e}")
        return False

if __name__ == "__main__":
    test_yaml_parsing()