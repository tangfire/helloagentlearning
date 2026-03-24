# clientRPRL.py
# APFL Client (Adaptive Prototype Fusion Learning) v1.4
# 核心机制：
#   - Learnable α gate with input [local, global]
#   - α clamp to [0.05, 0.95] for stability
#   - Adaptive EMA (confidence-aware momentum)
#   - Prototype consistency loss
#   - Class-wise sample count for aggregation
# 改进：
#   - 保存/加载 α 网络，防止每轮重新初始化
#   - 移除冗余设备转换
#   - α 网络 hidden size 32（原64）

import torch
import torch.nn as nn
import torch.nn.functional as F
import time
import numpy as np
from flcore.clients.clientbase import Client, load_item, save_item


class APFLClient(Client):
    def __init__(self, args, id, train_samples, test_samples, **kwargs):
        super().__init__(args, id, train_samples, test_samples, **kwargs)

        self.num_classes = args.num_classes
        self.feature_dim = getattr(args, "feature_dim", None)
        self.proto_scale = getattr(args, "proto_scale", 30.0)

        # 可学习 α 门控网络（将在确定 feature_dim 后加载或构建）
        self.alpha_net = None

        # 自适应 EMA 常数 k
        self.k_ema = getattr(args, "k_ema", 10.0)

        # 原型一致性损失权重
        self.lambda_proto = getattr(args, "lambda_proto", 0.2)

        # EMA 本地原型
        self.local_proto_ema = {}

        # 本地有样本的类别
        self.local_classes = self._get_local_classes()
        self.seen_mask = torch.zeros(self.num_classes, dtype=torch.bool)
        self.seen_mask[self.local_classes] = True

        # 类别样本数
        self.class_counts = self._compute_class_counts().float()

        self._feature_dim_determined = False

        print(f"[Client {id}] APFL v1.4 (Final Elegant Core) | "
              f"proto_scale={self.proto_scale}, local_classes={len(self.local_classes)}, "
              f"k_ema={self.k_ema}, lambda_proto={self.lambda_proto}")

    def _get_local_classes(self):
        trainloader = self.load_train_data()
        classes = set()
        for _, y in trainloader:
            for label in y:
                classes.add(int(label))
        return list(classes)

    def _compute_class_counts(self):
        counts = torch.zeros(self.num_classes, dtype=torch.int)
        trainloader = self.load_train_data()
        for _, y in trainloader:
            for label in y:
                counts[label] += 1
        return counts

    def _determine_feature_dim(self, model, trainloader):
        if self.feature_dim is not None:
            return self.feature_dim
        model.eval()
        with torch.no_grad():
            dummy_x, _ = next(iter(trainloader))
            dummy_x = dummy_x[:1].to(self.device)
            dummy_feat = model.base(dummy_x)
            self.feature_dim = dummy_feat.shape[1]
        model.train()
        return self.feature_dim

    def _build_alpha_net(self):
        """创建可学习 α 门控网络，输入为 [local, global] 拼接，隐藏层 32"""
        input_dim = self.feature_dim * 2
        self.alpha_net = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        ).to(self.device)
        print(f"[Client {self.id}] Alpha network created, input_dim={input_dim}, hidden=32")

    def _update_local_proto_ema(self, batch_protos):
        """自适应动量更新 EMA 本地原型"""
        with torch.no_grad():
            for c, proto in batch_protos.items():
                proto_cpu = proto.cpu().clone()
                count = self.class_counts[c].item()
                beta = count / (count + self.k_ema)
                if c not in self.local_proto_ema:
                    self.local_proto_ema[c] = proto_cpu
                else:
                    self.local_proto_ema[c] = (
                        (1 - beta) * self.local_proto_ema[c] +
                        beta * proto_cpu
                    )
                    self.local_proto_ema[c] = F.normalize(self.local_proto_ema[c], dim=0)

    def _compute_alpha(self, global_p, local_p):
        """
        使用门控网络计算 α，输入为 [local, global]。
        注意：global_p 和 local_p 已确保在同一设备且已归一化。
        """
        inp = torch.cat([local_p, global_p], dim=0).unsqueeze(0)  # [1, 2*feat_dim]
        alpha = self.alpha_net(inp).squeeze()
        # 限制范围，防止极端值
        alpha = torch.clamp(alpha, 0.05, 0.95)
        return alpha

    def train(self):
        trainloader = self.load_train_data()
        model = load_item(self.role, 'model', self.save_folder_name)
        if model is None:
            model = self.model

        # 加载全局原型
        global_protos = load_item('Server', 'global_protos', self.save_folder_name) or {}
        global_protos_norm = {}
        for c, p in global_protos.items():
            global_protos_norm[c] = F.normalize(p.to(self.device), dim=0).clone().detach()

        model.to(self.device)
        model.train()

        # 确定特征维度
        if not self._feature_dim_determined:
            self.feature_dim = self._determine_feature_dim(model, trainloader)
            self._feature_dim_determined = True

        # 加载或构建 α 网络
        self.alpha_net = load_item(self.role, 'alpha_net', self.save_folder_name)
        if self.alpha_net is not None:
            self.alpha_net.to(self.device)
            print(f"[Client {self.id}] Alpha network loaded from disk.")
        else:
            self._build_alpha_net()

        # 优化器：同时优化特征提取器和 α 网络
        params = list(model.base.parameters()) + list(self.alpha_net.parameters())
        optimizer = torch.optim.SGD(
            params,
            lr=self.learning_rate,
            momentum=0.9,
            weight_decay=1e-4
        )

        start_time = time.time()
        max_local_epochs = self.local_epochs
        if self.train_slow:
            max_local_epochs = np.random.randint(1, max_local_epochs)

        for step in range(max_local_epochs):
            for i, (x, y) in enumerate(trainloader):
                x, y = x.to(self.device), y.to(self.device)

                if self.train_slow:
                    time.sleep(0.1 * np.abs(np.random.rand()))

                features = model.base(x)
                features_norm = F.normalize(features, dim=1)

                # 计算batch原型（有梯度）
                batch_protos = {}
                unique_labels = y.unique().tolist()
                for c in unique_labels:
                    mask = (y == c)
                    if mask.sum() == 0:
                        continue
                    class_feats = features_norm[mask]
                    proto = class_feats.mean(dim=0)
                    proto = F.normalize(proto, dim=0)
                    batch_protos[c] = proto

                # 更新 EMA（使用detach的batch protos）
                self._update_local_proto_ema({c: p.detach() for c, p in batch_protos.items()})

                # 构建个人原型
                personal_protos = {}
                alpha_vals = {}
                for c in self.local_classes:
                    if c in global_protos_norm and c in self.local_proto_ema:
                        global_p = global_protos_norm[c]
                        local_p = self.local_proto_ema[c].to(self.device)
                        alpha = self._compute_alpha(global_p, local_p)
                        alpha_vals[c] = alpha.item()
                        proto = (1 - alpha) * global_p + alpha * local_p
                        proto = F.normalize(proto, dim=0)
                        personal_protos[c] = proto
                    elif c in global_protos_norm:
                        personal_protos[c] = global_protos_norm[c]
                    elif c in self.local_proto_ema:
                        personal_protos[c] = self.local_proto_ema[c].to(self.device)

                if not personal_protos:
                    continue

                # 构建分类 logits
                valid_classes = list(personal_protos.keys())
                P_mat = torch.stack([personal_protos[c] for c in valid_classes])
                class_to_idx = {c: idx for idx, c in enumerate(valid_classes)}

                cos_theta = features_norm @ P_mat.T  # [batch, num_valid]
                scaled_logits = cos_theta * self.proto_scale

                full_logits = torch.full((features_norm.shape[0], self.num_classes), -float('inf'), device=self.device)
                for c in valid_classes:
                    idx = class_to_idx[c]
                    full_logits[:, c] = scaled_logits[:, idx]

                # 交叉熵损失
                loss_ce = F.cross_entropy(full_logits, y)

                # --- 原型一致性损失 (target = personal proto, detach) ---
                proto_loss = torch.tensor(0.0, device=self.device)
                count = 0
                for c in unique_labels:
                    if c in personal_protos:
                        mask = (y == c)
                        if mask.sum() == 0:
                            continue
                        target_proto = personal_protos[c].detach()
                        feats = features_norm[mask]
                        proto_loss += ((feats - target_proto) ** 2).sum(dim=1).mean()
                        count += 1
                if count > 0:
                    proto_loss = proto_loss / count

                # 总损失
                loss = loss_ce + self.lambda_proto * proto_loss

                if i % 60 == 0:
                    alpha_str = ", ".join([f"c{k}:{v:.3f}" for k, v in list(alpha_vals.items())[:3]])
                    print(f"DEBUG Client {self.id} Batch {i}: CE={loss_ce.item():.4f}, Proto={proto_loss.item():.4f}, αs=[{alpha_str}]")

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

        # 训练结束后计算最终个人原型
        personal_protos_final = {}
        for c in global_protos_norm.keys():
            if c in self.local_proto_ema:
                global_p = global_protos_norm[c]
                local_p = self.local_proto_ema[c].to(self.device)
                alpha = self._compute_alpha(global_p, local_p)
                proto = (1 - alpha) * global_p + alpha * local_p
                proto = F.normalize(proto, dim=0)
                personal_protos_final[c] = proto.cpu()
            else:
                personal_protos_final[c] = global_protos_norm[c].cpu()

        for c in self.local_proto_ema.keys():
            if c not in personal_protos_final:
                personal_protos_final[c] = self.local_proto_ema[c]

        # 保存所有需要持久化的组件
        save_item(model, self.role, 'model', self.save_folder_name)
        save_item(self.alpha_net, self.role, 'alpha_net', self.save_folder_name)  # 新增：保存 α 网络
        save_item(personal_protos_final, self.role, 'personal_protos', self.save_folder_name)
        save_item(self.local_proto_ema, self.role, 'local_proto_ema', self.save_folder_name)
        save_item(self.class_counts.cpu(), self.role, 'class_counts', self.save_folder_name)
        save_item(self.seen_mask.cpu(), self.role, 'seen_mask', self.save_folder_name)

        self.train_time_cost['total_cost'] += time.time() - start_time
        self.train_time_cost['num_rounds'] += 1

    def test_metrics(self):
        testloader = self.load_test_data()
        model = load_item(self.role, 'model', self.save_folder_name)
        if model is None:
            model = self.model
        personal_protos = load_item(self.role, 'personal_protos', self.save_folder_name) or {}
        personal_protos = {c: p.to(self.device) for c, p in personal_protos.items()}
        seen_mask = self.seen_mask.to(self.device)

        model.to(self.device)
        model.eval()

        test_acc = 0
        test_num = 0
        with torch.no_grad():
            for x, y in testloader:
                x, y = x.to(self.device), y.to(self.device)
                features = model.base(x)
                features_norm = F.normalize(features, dim=1)

                if personal_protos:
                    valid_classes = list(personal_protos.keys())
                    P_mat = torch.stack([personal_protos[c] for c in valid_classes])
                    class_to_idx = {c: idx for idx, c in enumerate(valid_classes)}
                    cos_theta = features_norm @ P_mat.T
                    scaled_logits = cos_theta * self.proto_scale

                    full_logits = torch.full((features_norm.shape[0], self.num_classes), -float('inf'), device=self.device)
                    for c in valid_classes:
                        idx = class_to_idx[c]
                        full_logits[:, c] = scaled_logits[:, idx]
                else:
                    full_logits = model.head(features_norm)

                full_logits[:, ~seen_mask] = -float('inf')
                pred = torch.argmax(full_logits, dim=1)
                test_acc += (pred == y).sum().item()
                test_num += y.shape[0]

        return test_acc, test_num