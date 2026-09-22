"""Deterministic engineering-task reasoning over Forge codebase facts.

This module deliberately does not read or modify source files.  It consumes
the repository analysis produced by :class:`RepositoryAnalyzer` and returns
small JSON-serializable structures that a later LLM or execution phase can
use without changing the repository itself.
"""

from __future__ import annotations

import copy
import re
from collections import defaultdict
from typing import Any

from app.services.codebase import CodebaseContext


TASK_TYPES = {
    "feature",
    "bug_fix",
    "refactor",
    "test",
    "documentation",
    "configuration",
    "investigation",
    "unknown",
}

_CLASSIFICATION_RULES = (
    ("investigation", ("investigate", "investigation", "analyze", "analysis", "understand")),
    ("bug_fix", ("bug", "fix", "broken", "error", "incorrect", "regression")),
    ("refactor", ("refactor", "restructure", "simplify", "cleanup", "clean up")),
    ("documentation", ("document", "documentation", "readme", "docs")),
    ("configuration", ("config", "configuration", "setting", "environment")),
    ("test", ("test", "tests", "pytest", "coverage", "assertion")),
    ("feature", ("add", "implement", "support", "introduce", "feature", "enable")),
)

_STOP_WORDS = {
    "a", "an", "and", "as", "at", "be", "by", "for", "from", "in", "into",
    "is", "it", "of", "on", "or", "the", "to", "with", "this", "that", "please",
    "we", "should", "would", "could", "i", "our", "will",
}


class EngineeringBrain:
    """Plan engineering work from an already-computed repository analysis."""

    def __init__(self, analysis: dict[str, Any] | None = None) -> None:
        self.analysis = copy.deepcopy(analysis) if isinstance(analysis, dict) else {}
        self.understanding = self.analysis.get("codebase_understanding", {})
        self.context = CodebaseContext(self.understanding)
        self._files = self.understanding.get("files", [])
        self._modules = self.understanding.get("modules", [])
        self._symbols = self.understanding.get("symbols", [])
        self._components = self.understanding.get("components", [])
        self._summaries = self.understanding.get("summaries", {})

    def parse_task(self, task: str | dict[str, Any] | None) -> dict[str, Any]:
        """Normalize a task without inventing missing requirements."""
        if isinstance(task, dict):
            description = self._text(task.get("description"))
            explicit_type = self._normalize_type(task.get("type"))
            scope = self._strings(task.get("scope"))
            targets = self._strings(task.get("targets"))
            constraints = self._strings(task.get("constraints"))
            criteria = self._strings(task.get("acceptance_criteria"))
            assumptions = self._strings(task.get("assumptions"))
        else:
            description = self._text(task)
            explicit_type = None
            scope = []
            targets = []
            constraints = []
            criteria = []
            assumptions = []

        classification = self.classify_task(
            description,
            explicit_type=explicit_type,
        )
        return copy.deepcopy({
            "description": description,
            "type": classification["type"],
            "confidence": classification["confidence"],
            "classification_evidence": classification["evidence"],
            "scope": sorted(set(scope)),
            "targets": sorted(set(targets)),
            "constraints": sorted(set(constraints)),
            "acceptance_criteria": sorted(set(criteria)),
            "assumptions": sorted(set(assumptions)),
        })

    def classify_task(
        self,
        task: str | dict[str, Any] | None,
        *,
        explicit_type: str | None = None,
    ) -> dict[str, Any]:
        """Classify using visible keyword evidence and conservative confidence."""
        if isinstance(task, dict):
            if explicit_type is None:
                explicit_type = self._normalize_type(task.get("type"))
            description = self._text(task.get("description"))
        else:
            description = self._text(task)

        if explicit_type in TASK_TYPES and explicit_type != "unknown":
            return {
                "type": explicit_type,
                "confidence": "high",
                "evidence": ["task explicitly supplied this type"],
            }

        lowered = description.lower()
        matches = []
        evidence = []
        for task_type, terms in _CLASSIFICATION_RULES:
            found = [term for term in terms if self._term_matches(lowered, term)]
            if found:
                matches.append(task_type)
                evidence.append(
                    f"task contains {task_type} terminology: {', '.join(sorted(found))}"
                )

        if not matches:
            return {
                "type": "unknown",
                "confidence": "low",
                "evidence": ["no recognized task classification terminology"],
            }

        selected = matches[0]
        confidence = "high" if len(matches) == 1 else "medium"
        return copy.deepcopy({
            "type": selected,
            "confidence": confidence,
            "evidence": sorted(evidence),
        })

    def retrieve_context(
        self,
        task: str | dict[str, Any] | None,
        *,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Return a compact, ranked context package without source contents."""
        normalized = self.parse_task(task)
        scope = self.analyze_scope(normalized, limit=limit)
        paths = set(scope["relevant_files"])
        modules = [module for module in self._modules if module["path"] in paths]
        symbols = [symbol for symbol in self._symbols if symbol["file"] in paths]
        ranked = scope["ranked_files"]
        return copy.deepcopy({
            "repository": {
                "summary": self.analysis.get("summary", {}),
                "project_type": self.analysis.get("project_type", "unknown"),
                "architecture": self.analysis.get("architecture", {}),
                "frameworks": sorted(self.analysis.get("frameworks", [])),
            },
            "task": normalized,
            "ranked_files": ranked,
            "files": [file for file in self._files if file["path"] in paths],
            "modules": sorted(modules, key=lambda item: item["path"]),
            "symbols": sorted(
                symbols,
                key=lambda item: (item["file"], item["line"], item["name"]),
            ),
            "summaries": {
                path: self._summaries[path]
                for path in sorted(paths)
                if path in self._summaries
            },
            "tests": self._related_tests(paths, normalized),
            "entry_points": self._related_entry_points(paths),
            "configuration": sorted(
                path
                for path in self.understanding.get("configuration_files", [])
                if path in paths or normalized["type"] == "configuration"
            ),
        })

    def rank_relevance(
        self,
        task: str | dict[str, Any] | None,
        *,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Rank files with explainable, internal relevance scores."""
        normalized = self.parse_task(task)
        ranked = self._rank_files(normalized)
        return ranked[:limit] if limit is not None else ranked

    def analyze_scope(
        self,
        task: str | dict[str, Any],
        *,
        limit: int = 20,
    ) -> dict[str, Any]:
        normalized = task if self._is_normalized_task(task) else self.parse_task(task)
        ranked = self._rank_files(normalized)
        explicit_paths = self._explicit_target_paths(normalized)
        if explicit_paths:
            selected = [item for item in ranked if item["path"] in explicit_paths]
        else:
            selected = [item for item in ranked if item["score"] > 0][:max(limit, 0)]
        paths = {item["path"] for item in selected}
        explicit_targets = set(normalized["targets"]) | set(normalized["scope"])
        return copy.deepcopy({
            "relevant_files": sorted(paths),
            "relevant_modules": sorted(
                module["module"]
                for module in self._modules
                if module["path"] in paths
            ),
            "relevant_symbols": [
                symbol
                for symbol in self._symbols
                if symbol["file"] in paths
            ],
            "affected_components": self._components_for_paths(paths),
            "affected_layers": self._layers_for_paths(paths),
            "related_tests": self._related_tests(paths, normalized),
            "entry_points": self._related_entry_points(paths),
            "ranked_files": ranked[:max(limit, 0)],
            "uncertain": not bool(paths) or bool(explicit_targets - paths),
        })

    def analyze_impact(
        self,
        task: str | dict[str, Any],
        scope: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized = task if self._is_normalized_task(task) else self.parse_task(task)
        scope = scope or self.analyze_scope(normalized)
        direct_targets = set(scope.get("relevant_files", []))
        dependencies = set()
        dependents = set()
        for path in direct_targets:
            dependencies.update(self.context.local_dependencies(path))
            dependents.update(self.context.local_dependents(path))
        return {
            "direct_targets": sorted(direct_targets),
            "dependencies": sorted(dependencies - direct_targets),
            "dependents": sorted(dependents - direct_targets),
            "tests": sorted(set(scope.get("related_tests", []))),
            "entry_points": sorted(set(scope.get("entry_points", []))),
            "components": self._components_for_paths(
                direct_targets | dependencies | dependents
            ),
            "layers": self._layers_for_paths(
                direct_targets | dependencies | dependents
            ),
        }

    def detect_ambiguity(
        self,
        task: str | dict[str, Any] | None,
        scope: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized = task if self._is_normalized_task(task) else self.parse_task(task)
        scope = scope or self.analyze_scope(normalized)
        questions = []
        description_tokens = self._keywords(normalized["description"])
        if not description_tokens:
            questions.append("What engineering behavior should Forge plan?")
        if not self._files:
            questions.append("Which repository or component should this task target?")
        elif not scope.get("relevant_files"):
            questions.append("Which repository file, module, or component should this task target?")
        if normalized["targets"]:
            known = set(self._all_paths_and_names())
            missing = [target for target in normalized["targets"] if target not in known]
            if missing:
                questions.append(
                    "Clarify the requested target: " + ", ".join(sorted(missing))
                )
        if len(scope.get("relevant_files", [])) > 10 and not normalized["targets"]:
            questions.append("Which of the broadly matching files is the intended change surface?")
        return {
            "needs_clarification": bool(questions),
            "questions": sorted(set(questions)),
        }

    def analyze_risks(
        self,
        task: str | dict[str, Any],
        scope: dict[str, Any] | None = None,
        impact: dict[str, Any] | None = None,
        ambiguity: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        normalized = task if self._is_normalized_task(task) else self.parse_task(task)
        scope = scope or self.analyze_scope(normalized)
        impact = impact or self.analyze_impact(normalized, scope)
        ambiguity = ambiguity or self.detect_ambiguity(normalized, scope)
        risks = []
        for path in impact["direct_targets"]:
            dependents = self.context.local_dependents(path)
            if len(dependents) >= 2:
                risks.append({
                    "type": "high_fanout",
                    "description": f"{path} has multiple local dependents.",
                    "evidence": sorted(dependents),
                })
            if path in set(self.analysis.get("entry_points", [])):
                risks.append({
                    "type": "entry_point_change",
                    "description": f"{path} is a detected entry point.",
                    "evidence": [path],
                })
            if path in set(self.understanding.get("configuration_files", [])):
                risks.append({
                    "type": "configuration_change",
                    "description": f"{path} is a recognized configuration file.",
                    "evidence": [path],
                })
            unresolved = self.understanding.get("dependency_graph", {}).get(path, {}).get("unresolved", [])
            if unresolved:
                risks.append({
                    "type": "unresolved_dependency",
                    "description": f"{path} has unresolved imports.",
                    "evidence": sorted(unresolved),
                })
        if ambiguity["needs_clarification"]:
            risks.append({
                "type": "ambiguous_task_scope",
                "description": "The task does not identify a sufficiently safe change surface.",
                "evidence": ambiguity["questions"],
            })
        if len(impact["direct_targets"]) > 10:
            risks.append({
                "type": "large_affected_area",
                "description": "The inferred change surface is broad.",
                "evidence": [str(len(impact["direct_targets"])) + " direct targets"],
            })
        public_symbols = [
            symbol["name"]
            for symbol in scope.get("relevant_symbols", [])
            if symbol.get("visibility") == "public"
        ]
        if public_symbols:
            risks.append({
                "type": "public_api_change",
                "description": "The inferred scope includes public symbols.",
                "evidence": sorted(set(public_symbols)),
            })
        if not impact["tests"]:
            risks.append({
                "type": "test_coverage_uncertainty",
                "description": "No relevant existing test file was identified.",
                "evidence": ["no related tests found in the codebase model"],
            })
        return sorted(risks, key=lambda item: (item["type"], item["description"]))

    def generate_test_strategy(
        self,
        task: str | dict[str, Any],
        scope: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized = task if self._is_normalized_task(task) else self.parse_task(task)
        scope = scope or self.analyze_scope(normalized)
        existing = sorted(set(scope.get("related_tests", [])))
        proposed = []
        if normalized["type"] == "test":
            proposed.append("Add or update tests for the requested behavior and its edge cases.")
        else:
            proposed.append("Add regression coverage for the changed behavior.")
        if normalized["type"] in {"feature", "bug_fix", "refactor"}:
            proposed.append("Cover invalid, empty, and unresolved-input behavior where applicable.")
        if not existing:
            proposed.append("Identify the repository's existing pytest location before adding coverage.")
        return {
            "existing_tests": existing,
            "proposed_tests": proposed,
            "categories": ["targeted behavior", "regression", "edge cases"],
            "validation_commands": ["python -m pytest -q"],
        }

    def generate_plan(self, task: str | dict[str, Any] | None) -> dict[str, Any]:
        normalized = self.parse_task(task)
        scope = self.analyze_scope(normalized)
        impact = self.analyze_impact(normalized, scope)
        ambiguity = self.detect_ambiguity(normalized, scope)
        tests = self.generate_test_strategy(normalized, scope)
        risks = self.analyze_risks(normalized, scope, impact, ambiguity)
        assumptions = self._assumptions(normalized, scope)
        steps = self._plan_steps(normalized, scope, tests)
        confidence = self._plan_confidence(normalized, scope, ambiguity, tests)
        return copy.deepcopy({
            "task": normalized,
            "objective": normalized["description"] or "Clarify the intended engineering objective.",
            "context": self.retrieve_context(normalized),
            "scope": scope,
            "impact": impact,
            "affected_files": sorted(set(impact["direct_targets"])),
            "affected_symbols": scope["relevant_symbols"],
            "steps": steps,
            "tests": tests,
            "risks": risks,
            "assumptions": assumptions,
            "ambiguity": ambiguity,
            "confidence": confidence,
            "validation": ["python -m pytest -q"],
        })

    plan = generate_plan

    def _rank_files(self, task: dict[str, Any]) -> list[dict[str, Any]]:
        keywords = self._keywords(task["description"])
        explicit = set(task["targets"]) | set(task["scope"])
        explicit_paths = self._explicit_target_paths(task)
        related_dependencies = {
            dependency
            for path in explicit_paths
            for dependency in self.context.local_dependencies(path)
        }
        related_dependents = {
            dependent
            for path in explicit_paths
            for dependent in self.context.local_dependents(path)
        }
        related_tests = set(self._related_tests(explicit_paths, task))
        related_entry_points = set(self._related_entry_points(explicit_paths))
        ranked = []
        for file in self._files:
            path = file["path"]
            path_lower = path.lower()
            score = 0
            reasons = []
            path_stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
            module = file.get("module") or ""
            symbol_names = {
                symbol["name"].lower()
                for symbol in self._symbols
                if symbol["file"] == path
            }
            for target in sorted(explicit):
                target_lower = target.lower().replace("\\", "/")
                if target_lower == path_lower:
                    score += 10
                    reasons.append("exact target file match")
                elif target_lower == module.lower():
                    score += 9
                    reasons.append("exact target module match")
                elif target_lower in path_lower:
                    score += 5
                    reasons.append("target path match")
                elif target_lower in symbol_names:
                    score += 8
                    reasons.append("exact target symbol match")
            for keyword in keywords:
                if keyword in path_lower or keyword == path_stem or keyword in module.lower():
                    score += 2
                    reasons.append(f"task keyword matched {keyword}")
            for keyword in keywords:
                if keyword in symbol_names:
                    score += 5
                    reasons.append(f"task keyword matched symbol {keyword}")
            component_hits = self._component_names_for_path(path) & keywords
            for component in sorted(component_hits):
                score += 3
                reasons.append(f"task keyword matched component {component}")
            if path in related_dependencies:
                score += 1
                reasons.append("local dependency of target module")
            if path in related_dependents:
                score += 1
                reasons.append("local dependent of target module")
            if path in related_entry_points:
                score += 1
                reasons.append("entry-point relationship")
            if path in related_tests:
                score += 1
                reasons.append("related test file")
            if score:
                ranked.append({"path": path, "score": score, "reasons": sorted(set(reasons))})

        ranked.sort(key=lambda item: (-item["score"], item["path"]))
        return ranked

    def _plan_steps(
        self,
        task: dict[str, Any],
        scope: dict[str, Any],
        tests: dict[str, Any],
    ) -> list[dict[str, Any]]:
        targets = scope["relevant_files"]
        if not targets:
            return [{
                "order": 1,
                "description": "Clarify the intended repository target before implementation planning.",
                "targets": [],
                "depends_on": [],
            }]
        steps = [{
            "order": 1,
            "description": "Inspect the identified implementation surface and confirm the requested behavior.",
            "targets": targets,
            "depends_on": [],
        }]
        steps.append({
            "order": 2,
            "description": "Implement the requested change while preserving existing repository contracts.",
            "targets": targets,
            "depends_on": [1],
        })
        steps.append({
            "order": 3,
            "description": "Add or update targeted regression coverage for the requested behavior.",
            "targets": tests["existing_tests"],
            "depends_on": [2],
        })
        steps.append({
            "order": 4,
            "description": "Run the proposed validation checks and review affected dependents.",
            "targets": sorted(set(scope["relevant_files"]) | set(impact_path for impact_path in scope["related_tests"])),
            "depends_on": [2, 3],
        })
        return steps

    def _assumptions(self, task: dict[str, Any], scope: dict[str, Any]) -> list[str]:
        assumptions = set(task["assumptions"])
        if self.analysis.get("summary", {}).get("test_files", 0):
            assumptions.add("The existing pytest-based test workflow remains the validation baseline.")
        if self.analysis.get("frameworks"):
            assumptions.add("Existing detected frameworks remain in use unless the task explicitly requests a change.")
        if scope["relevant_files"]:
            assumptions.add("The inferred relevant files are a planning scope, not permission to modify them automatically.")
        return sorted(assumptions)

    def _plan_confidence(
        self,
        task: dict[str, Any],
        scope: dict[str, Any],
        ambiguity: dict[str, Any],
        tests: dict[str, Any],
    ) -> str:
        if ambiguity["needs_clarification"]:
            return "low"
        if task["targets"] and scope["relevant_files"] and tests["existing_tests"]:
            return "high"
        if scope["relevant_files"]:
            return "medium"
        return "low"

    def _related_tests(self, paths: set[str], task: dict[str, Any]) -> list[str]:
        tests = set(self.understanding.get("test_files", []))
        if task["type"] == "test":
            return sorted(tests)
        names = set()
        for path in paths:
            stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
            names.add(stem.replace("_", ""))
        related = []
        for test in tests:
            lowered = test.lower().replace("_", "")
            if any(name and name in lowered for name in names):
                related.append(test)
        return sorted(related)

    def _related_entry_points(self, paths: set[str]) -> list[str]:
        entry_points = set(self.analysis.get("entry_points", []))
        entry_context = self.understanding.get("entry_point_context", [])
        related = entry_points.intersection(paths)
        for entry in entry_context:
            if entry["path"] in paths or paths.intersection(entry.get("local_imports", [])):
                related.add(entry["path"])
        return sorted(related)

    def _explicit_target_paths(self, task: dict[str, Any]) -> set[str]:
        targets = set(task["targets"]) | set(task["scope"])
        if not targets:
            return set()
        paths = {file["path"] for file in self._files}
        modules = {module["module"]: module["path"] for module in self._modules}
        symbols = defaultdict(set)
        for symbol in self._symbols:
            symbols[symbol["name"]].add(symbol["file"])
        resolved = set()
        for target in targets:
            normalized = target.replace("\\", "/")
            if normalized in paths:
                resolved.add(normalized)
            elif target in modules:
                resolved.add(modules[target])
            else:
                resolved.update(symbols.get(target, set()))
        return resolved

    def _components_for_paths(self, paths: set[str]) -> list[str]:
        components = {
            component["name"]
            for component in self._components
            if paths.intersection(component.get("files", []))
        }
        layer_names = set(self.understanding.get("layers", []))
        for layer in layer_names:
            if any(
                layer.lower() in {
                    part.lower()
                    for path in paths
                    for part in path.split("/")
                }
                or layer.lower() in path.rsplit("/", 1)[-1].lower()
                for path in paths
            ):
                components.add(layer)
        return sorted(components)

    def _layers_for_paths(self, paths: set[str]) -> list[str]:
        layers = set()
        for path in paths:
            parts = {part.lower() for part in path.split("/")}
            for layer in self.understanding.get("layers", []):
                if layer.lower() in parts:
                    layers.add(layer)
        return sorted(layers)

    def _component_names_for_path(self, path: str) -> set[str]:
        return {
            component["name"].lower()
            for component in self._components
            if path in component.get("files", [])
        }

    def _all_paths_and_names(self) -> list[str]:
        values = [file["path"] for file in self._files]
        values.extend(module["module"] for module in self._modules)
        values.extend(symbol["name"] for symbol in self._symbols)
        return values

    @staticmethod
    def _is_normalized_task(task: Any) -> bool:
        return isinstance(task, dict) and {
            "description", "type", "targets", "scope", "assumptions"
        }.issubset(task)

    @staticmethod
    def _normalize_type(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        return normalized if normalized in TASK_TYPES else None

    @staticmethod
    def _text(value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return " ".join(value.split())[:100_000]

    @classmethod
    def _strings(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, (list, tuple, set)):
            values = list(value)
        else:
            values = []
        return sorted({text for item in values if (text := cls._text(item))})

    @staticmethod
    def _keywords(value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_/-]*", value.lower())
            if token not in _STOP_WORDS and len(token) > 1
        }

    @staticmethod
    def _term_matches(value: str, term: str) -> bool:
        pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
        return re.search(pattern, value, re.IGNORECASE) is not None


EngineeringBrainService = EngineeringBrain