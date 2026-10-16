---
title: AE，VAE和ELBO
date: 2026-10-16
category: 概念理解
summary: 从 AE 的潜空间出发，理解 VAE 的生成模型、变分推断与 ELBO。
summary_en: Notes on AE latent spaces, VAE generative models, variational inference, and the ELBO.
draft: false
---

2026/10/16 12:17

## AE，VAE与ELBO

AE包含Encoder和Decoder。现在有一张图片，我们可以观测到的，我们称其为Observed variable $x$。有latent variable $z$。$\hat{x}$为重构结果，

$$
x \xrightarrow{f_\phi} z \xrightarrow{g_\theta} \hat{x}
$$

训练时，我们尽可能让$\hat{x}$接近$x$。对于固定的模型参数，同一个输入$x$会有确定的$z=f_\phi(x)$。但现在我们想没有新输入，直接生成$\hat{x}$，这时要先有一个$z_{\mathrm{new}}$，再给decoder生成，但此时就有问题了，AE的重构目标，无规定如何采样$z_{\mathrm{new}}$，其主要约束training data encoding后的位置，保证不了在Latent space随意取一点，都能decode成合理图片。

{{figure:ae}}

为了让生成过程能顺利，可假设latent variable来自一个容易sample的分布，比如$z\sim p(z)=N(0,1)$，之后可用decoder描述给定$z$时如何生成数据：$x\sim p_\theta(x\mid z)$，此时完整的生成model为：

$$
p(z)p_\theta(x\mid z)=p_\theta(x,z)
$$

{{figure:vae}}

在这个生成model下，把observed variable $x$服从的分布$p_\theta(x)$为：

$$
p_\theta(x)=\int p_\theta(x,z)\,dz=\int p(z)p_\theta(x\mid z)\,dz
$$

为什么是observed variable $x$的分布？不应该是生成的图片的分布吗？VAE想学的不是某一个具体image的重构分布，而是整个data space里的真实image应服从什么分布。

生成model的方向是$z\to x$。但在training时，我们只有image $x$，latent variable是不可见的，此时我们就想知道当前model在观察这张图片后，哪些$z$更可能解释观测，此时可描述为：

$$
p_\theta(z\mid x),\qquad p_\theta(z\mid x)=\frac{p_\theta(x\mid z)p(z)}{p_\theta(x)}
$$

$p(z)$为先验，既未观测$x$时我们对$z$的假设。

$p_\theta(z\mid x)$为后验，既观测$x$后，在当前model下对$z$的推断。VAE不用像AE样让每个$x$对应的唯一的latent variable，而是用$p_\theta(z\mid x)$描述给定$x$，不同的$z$的概率有多大。

现在的问题是$p_\theta(z\mid x)$难以计算，因为$p_\theta(x)=\int p(z)p_\theta(x\mid z)\,dz$，称为边缘似然，需要对$z$在整个支撑集上做遍历式积分，并按先验$p(z)$加权，难以计算。

此时聪明的前人想到，既然算不了，不如构造一个可计算，可优化的分布$q_\phi(z\mid x)$，让其一点点逼近真实的$p_\theta(z\mid x)$。

{{figure:variational}}

在一个分布族中寻找合适的分布，让其近似于真实的后验，这就是变分推断的基本思路。为了衡量做近似误差，很自然地想到用KL散度来衡量。对于假设的生成模型参数$\theta$，我们希望

$$
\min_\phi D_{\mathrm{KL}}\!\left(q_\phi(z\mid x)\,\|\,p_\theta(z\mid x)\right)
$$

## ELBO

但该式子还是有$p_\theta(z\mid x)$，还需要改写成可计算形式：

$$
D_{\mathrm{KL}}\!\left(q_\phi(z\mid x)\,\|\,p_\theta(z\mid x)\right)
=\mathbb{E}_{q_\phi(z\mid x)}\!\left[\log\frac{q_\phi(z\mid x)}{p_\theta(z\mid x)}\right]
$$

而

$$
p_\theta(z\mid x)=\frac{p_\theta(x,z)}{p_\theta(x)}
$$

$$
\begin{aligned}
D_{\mathrm{KL}}\!\left(q_\phi(\cdot)\,\|\,p_\theta(\cdot)\right)
&=\mathbb{E}_{q_\phi(z\mid x)}\!\left[\log q_\phi(z\mid x)\right.\\
&\qquad\left.-\log p_\theta(x,z)+\log p_\theta(x)\right]
\end{aligned}
$$

而$\log p_\theta(x)$不依赖于随机变量$z$，可直接移到期望之外，

则

$$
\begin{aligned}
D_{\mathrm{KL}}\!\left(q_\phi(\cdot)\,\|\,p_\theta(\cdot)\right)
&=\log p_\theta(x)\\
&\quad-\mathbb{E}_{q_\phi(z\mid x)}\!\left[\log p_\theta(x,z)-\log q_\phi(z\mid x)\right]
\end{aligned}
$$

我们将$\mathbb{E}_{q_\phi(z\mid x)}[\log p_\theta(x,z)-\log q_\phi(z\mid x)]$定义为ELBO（Evidence Lower Bound，证据下界）$L_{\mathrm{ELBO}}(\theta,\phi;x)$

$$
D_{\mathrm{KL}}\!\left(q_\phi(z\mid x)\,\|\,p_\theta(z\mid x)\right)=-\mathrm{ELBO}+\log p_\theta(x)
$$

$$
\Rightarrow\quad\underbrace{\log p_\theta(x)}_{\text{定值}}=\underbrace{D_{\mathrm{KL}}}_{\text{原任务最小化}}+\mathrm{ELBO}
$$

由于$D_{\mathrm{KL}}$有后验难以计算，但$D_{\mathrm{KL}}+\mathrm{ELBO}$为一个定值，则可将原先最小化$D_{\mathrm{KL}}$的问题转为最大化ELBO。

这就是ELBO的讲述，但ELBO到VAE最终损失函数仍有距离，下次再学了……
