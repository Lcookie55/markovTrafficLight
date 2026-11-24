# Equations of the report (LaTeX source)

## (1) m

```latex
M=(S,\;A,\;P,\;R,\;\gamma)
```

## (2) markov

```latex
P(S_{t+1}=s'\mid S_t=s,A_t=a,S_{t-1},A_{t-1},\ldots,S_0,A_0)
=P(S_{t+1}=s'\mid S_t=s,A_t=a)
```

## (3) return

```latex
G_t=\sum_{k=0}^{\infty}\gamma^{k}R_{t+k+1}=R_{t+1}+\gamma R_{t+2}+\gamma^{2}R_{t+3}+\cdots
```

## (4) vpi_def

```latex
V^{\pi}(s)=\mathbb{E}_{\pi}\left[G_t\mid S_t=s\right]=\mathbb{E}_{\pi}\left[\sum_{k=0}^{\infty}\gamma^{k}R_{t+k+1}\mid S_t=s\right]
```

## (5) qpi_def

```latex
Q^{\pi}(s,a)=\mathbb{E}_{\pi}\left[G_t\mid S_t=s,A_t=a\right]=\mathbb{E}_{\pi}\left[\sum_{k=0}^{\infty}\gamma^{k}R_{t+k+1}\mid S_t=s,A_t=a\right]
```

## (6) bellman_exp

```latex
V^{\pi}(s)=\sum_{a\in A}\pi(a\mid s)\sum_{s'\in S}P(s'\mid s,a)\left[R(s,a,s')+\gamma V^{\pi}(s')\right]
```

## (7) vstar

```latex
V^{*}(s)=\max_{a\in A}\sum_{s'\in S}P(s'\mid s,a)\left[R(s,a,s')+\gamma V^{*}(s')\right]
```

## (8) qstar

```latex
Q^{*}(s,a)=\sum_{s'\in S}P(s'\mid s,a)\left[R(s,a,s')+\gamma\max_{a'\in A}Q^{*}(s',a')\right]
```

## (9) pistar

```latex
\pi^{*}(s)=\arg\max_{a\in A}Q^{*}(s,a)
```

## (10) qlearn

```latex
Q(S_t,A_t)\leftarrow Q(S_t,A_t)+\alpha\left[R_{t+1}+\gamma\max_{a'}Q(S_{t+1},a')-Q(S_t,A_t)\right]
```

## (11) m2

```latex
M=(S,\;A,\;P,\;R,\;\gamma)
```

## (12) state

```latex
S_t=(q_{NS},\;q_{EW},\;p,\;e)
```

## (13) queue

```latex
q'=\min\left(q_{\max},\;\max\left(0,\;q+\mathrm{arrivals}-\mathrm{departures}\right)\right)
```

## (14) reward

```latex
R(s,a,s')=-\left(q'_{NS}+q'_{EW}\right)-c_{\mathrm{switch}}\cdot\mathbf{1}[a=\mathrm{SWITCH}]
```

## (15, 16) optimal

```latex
V^{*}(s)=\max_{a\in A}\sum_{s'\in S}P(s'\mid s,a)\left[R(s,a,s')+\gamma V^{*}(s')\right]
\pi^{*}(s)=\arg\max_{a\in A}Q^{*}(s,a)
```
