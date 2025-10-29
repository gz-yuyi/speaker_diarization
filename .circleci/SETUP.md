# CircleCI 迁移指南

本指南将帮助您从 GitHub Actions 迁移到 CircleCI 的 Docker 构建工作流。

## 前提条件

1. **CircleCI 账户**: 在 [circleci.com](https://circleci.com) 注册
2. **项目设置**: 将您的仓库添加到 CircleCI
3. **环境变量**: 在 CircleCI 中设置所需的密钥

## 必需的环境变量

在您的 CircleCI 项目设置中设置以下环境变量：

- `ALIYUN_REGISTRY_USERNAME`: 您的阿里云容器镜像服务用户名
- `ALIYUN_REGISTRY_PASSWORD`: 您的阿里云容器镜像服务密码
- `HF_TOKEN`: 您的 HuggingFace 令牌（可选，用于模型下载）

## 迁移步骤

### 1. 在您的仓库中启用 CircleCI

1. 访问 [CircleCI](https://circleci.com)
2. 导航到 "Projects"
3. 找到您的仓库并点击 "Set Up Project"
4. 选择 "Fastest: Use the .circleci/config.yml in my repo"

### 2. 配置环境变量

在您的 CircleCI 项目设置中：
1. 转到 "Project Settings" > "Environment Variables"
2. 添加上面提到的三个必需变量

### 3. 测试配置

将 `.circleci/config.yml` 文件推送到您的仓库。CircleCI 将自动检测配置并开始构建。

## 与 GitHub Actions 的主要差异

### 工作流触发器
- **GitHub Actions**: 在推送到 main/develop 分支和标签时触发
- **CircleCI**: 使用分支过滤器和标签过滤器实现类似行为

### Docker 构建过程
- **GitHub Actions**: 使用 Docker Buildx 和 GitHub Actions 缓存
- **CircleCI**: 使用 Docker Buildx 和 CircleCI 的远程 Docker 环境

### 密钥管理
- **GitHub Actions**: 使用仓库密钥
- **CircleCI**: 使用项目环境变量

## 配置详情

### 构建作业
CircleCI 配置包括：
- **Docker 设置**: 使用带层缓存的远程 Docker
- **镜像仓库登录**: 与阿里云容器镜像服务进行身份验证
- **标签生成**: 根据分支/标签创建适当的标签
- **多平台构建**: 为 linux/amd64 构建
- **构建参数**: 传递 HuggingFace 令牌用于可选的模型下载

### 工作流过滤器
- 在 `main` 和 `develop` 分支上构建
- 在版本标签 (`v*.*.*`) 上构建
- 处理到 `main` 分支的拉取请求

## 故障排除

### 常见问题

1. **Docker 登录失败**: 验证您的阿里云凭据
2. **构建缓存问题**: CircleCI 使用与 GitHub Actions 不同的缓存机制
3. **标签生成**: 检查标签生成逻辑是否符合您的要求

### 调试

- 检查 CircleCI 构建日志以获取详细的错误消息
- 验证环境变量是否正确设置
- 确保 Dockerfile 在本地正确构建

## 后续步骤

1. 使用测试分支测试 CircleCI 工作流
2. 监控前几次构建是否有问题
3. 稳定后，您可以禁用 GitHub Actions 工作流
4. 如果需要，更新您的部署流程

## 配置结构说明

```
.circleci/
├── config.yml          # 主要 CircleCI 配置
└── CIRCLE_CI_SETUP.md  # 本设置指南
```

### 工作流流程
1. **检出代码** → **设置 Docker** → **登录镜像仓库** → **提取元数据** → **构建推送镜像**

### 标签生成策略
- **分支**: `分支名`
- **拉取请求**: `pr-编号`
- **版本标签**: `版本号`, `主版本.次版本`, `主版本`
- **主分支**: `latest`

## 性能优化

- 使用 `resource_class: medium` 确保足够的构建资源
- 启用 Docker 层缓存以加速后续构建
- 使用多阶段构建减少最终镜像大小
