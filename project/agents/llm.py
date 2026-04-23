from __future__ import annotations

from project.algorithms import SUPPORTED_ALGORITHMS
from project.core.agent import Agent, AgentMessage
from project.llm import (
    LLMClient,
    LLMClientConfig,
    clamp_decision,
    parse_llm_decision,
    build_prompt,
    state_to_text,
)


class LLMAgent(Agent):
    def __init__(
        self,
        provider: str = "auto",
        model: str = "gpt-5.4-mini",
        temperature: float = 0.2,
        max_tokens: int = 300,
        timeout_seconds: int = 12,
        api_base_url: str = "https://api.openai.com",
        api_key_env: str = "OPENAI_API_KEY",
        allowed_algorithms: list[str] | None = None,
        allow_algorithm_override: bool = True,
        allow_node_bias_override: bool = True,
        name: str = "llm",
    ) -> None:
        super().__init__(name=name)
        self.client = LLMClient(
            LLMClientConfig(
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
                api_base_url=api_base_url,
                api_key_env=api_key_env,
            )
        )
        self.allowed_algorithms = set(allowed_algorithms or SUPPORTED_ALGORITHMS)
        self.allow_algorithm_override = allow_algorithm_override
        self.allow_node_bias_override = allow_node_bias_override

    def decide(self) -> None:
        if self.state is None or self.context is None:
            return
        node_ids = sorted(self.context.nodes.keys())
        state_text = state_to_text(self.state)
        prompt = build_prompt(state_text, sorted(self.allowed_algorithms), node_ids)
        response_text, source = self.client.complete(prompt, self.state, node_ids)
        parsed = parse_llm_decision(response_text, source=source)
        decision = clamp_decision(
            parsed,
            allowed_algorithms=self.allowed_algorithms,
            allowed_nodes=set(node_ids),
            allow_algorithm_override=self.allow_algorithm_override,
            allow_node_bias_override=self.allow_node_bias_override,
        )

        self.context.llm_source = source
        self.context.llm_confidence = decision.confidence
        self.context.llm_reason = decision.reason
        self.context.llm_raw_response = decision.raw
        self.context.llm_node_bias = dict(decision.node_bias)
        self.context.llm_algorithm_hint = decision.algorithm_hint
        self.context.llm_actions_applied += 1

        self.send(
            AgentMessage(
                sender=self.name,
                recipient="compute",
                topic="llm_policy",
                payload={
                    "node_bias": decision.node_bias,
                    "confidence": decision.confidence,
                    "reason": decision.reason,
                },
            )
        )
        if decision.algorithm_hint:
            self.send(
                AgentMessage(
                    sender=self.name,
                    recipient="optimization",
                    topic="llm_algorithm_hint",
                    payload={
                        "algorithm": decision.algorithm_hint,
                        "confidence": decision.confidence,
                        "reason": decision.reason,
                    },
                )
            )

        self.send(
            AgentMessage(
                sender=self.name,
                recipient="monitoring",
                topic="llm_decision",
                payload={
                    "source": source,
                    "confidence": decision.confidence,
                    "algorithm_hint": decision.algorithm_hint,
                },
            )
        )

    def act(self) -> None:
        return

