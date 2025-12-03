# 安装指南

## 常见问题：Command 'peotry' not found

这是一个简单的拼写错误，正确的命令是 `poetry` 而不是 `peotry`。

## 完整安装步骤

### 1. 安装Poetry（如果尚未安装）

#### 方法1：使用官方安装脚本（推荐）

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

#### 方法2：使用pip安装

```bash
pip install poetry
```

#### 方法3：在Ubuntu/Debian上使用apt安装

```bash
sudo apt update
sudo apt install python3-poetry
```

### 2. 验证Poetry安装

```bash
poetry --version
```

应该输出类似：
```
Poetry (version 1.7.1)
```

### 3. 安装项目依赖

进入项目目录后，使用正确的命令安装依赖：

```bash
poetry install
```

### 4. 激活虚拟环境

```bash
poetry shell
```

### 5. 验证安装

安装完成后，可以运行以下命令验证：

```bash
gpuctl --help
```

## 常见问题排查

### 问题1：Poetry命令找不到

如果安装后仍然提示 `command not found`，请确保Poetry的可执行文件路径已添加到系统PATH中。

- **对于官方安装脚本**：安装完成后会提示如何添加PATH，通常是：
  ```bash
export PATH="$HOME/.local/bin:$PATH"
```

- **对于pip安装**：确保Python的脚本目录在PATH中：
  ```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 问题2：依赖安装失败

- 确保Python版本符合要求（>=3.8）
- 检查网络连接是否正常
- 尝试清理Poetry缓存后重新安装：
  ```bash
  poetry cache clear --all pypi
  poetry install
  ```

### 问题3：虚拟环境问题

- 如果 `poetry shell` 无法激活环境，可以尝试使用 `poetry run` 直接运行命令：
  ```bash
  poetry run gpuctl --help
  ```

### 问题4：锁文件版本不兼容

**错误信息**：
```
RuntimeError
The lock file is not compatible with the current version of Poetry.
Upgrade Poetry to be able to read the lock file or, alternatively, regenerate the lock file with the `poetry lock` command.
```

**原因**：poetry.lock文件是由较新版本的Poetry（如2.2.1）生成的，而当前系统安装的Poetry版本（如1.1.12）无法识别该锁文件格式。

**解决方案**：

**方案1：升级Poetry到最新版本（推荐）**

```bash
# 使用官方安装脚本升级
curl -sSL https://install.python-poetry.org | python3 -

# 或使用pip升级
pip install --upgrade poetry
```

**方案2：重新生成锁文件**

如果不想升级Poetry，可以删除旧的锁文件并重新生成：

```bash
# 删除旧的锁文件
rm poetry.lock

# 重新生成锁文件
poetry lock

# 安装依赖
poetry install
```

**方案3：使用apt安装兼容版本**

如果使用apt安装，可以尝试安装与锁文件兼容的Poetry版本：

```bash
# 添加Poetry的官方仓库
sudo apt install curl python3-venv
test -d ~/.local/share/pypoetry || mkdir -p ~/.local/share/pypoetry
test -f ~/.local/share/pypoetry/installer.py || curl -sSL https://install.python-poetry.org -o ~/.local/share/pypoetry/installer.py
python3 ~/.local/share/pypoetry/installer.py --version 2.2.1
```

**注意**：重新生成锁文件可能会改变依赖版本，建议优先选择升级Poetry的方案。

## 快速参考

| 操作 | 命令 |
|------|------|
| 安装Poetry | `curl -sSL https://install.python-poetry.org | python3 -` |
| 安装项目依赖 | `poetry install` |
| 激活虚拟环境 | `poetry shell` |
| 运行gpuctl命令 | `poetry run gpuctl --help` |
| 查看Poetry版本 | `poetry --version` |
