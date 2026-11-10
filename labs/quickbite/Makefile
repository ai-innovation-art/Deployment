# QuickBite: one-word commands. Run `make` to see them.
NS ?= quickbite

.PHONY: help tools images push compose-up compose-down cluster resume status url reset down

help:
	@echo "First time ever (once):"
	@echo "  make images      build all images locally"
	@echo "  make push        build + push to Docker Hub (docker login first)"
	@echo "Every study session:"
	@echo "  make resume      checkpoint 'app': cluster + full QuickBite running"
	@echo "  make cluster     checkpoint 'cluster': empty 3-node cluster (Chapter 1)"
	@echo "  make status      nodes + pods, with the node each pod runs on"
	@echo "  make reset       delete QuickBite and deploy it fresh"
	@echo "Other:"
	@echo "  make compose-up  run QuickBite with plain Docker (no Kubernetes)"
	@echo "  make down        delete the kind cluster"

tools:
	bash scripts/install-tools.sh

images:
	bash scripts/build-push.sh

push:
	bash scripts/build-push.sh --push

compose-up:
	docker compose up -d --build && echo "open port 8080"

compose-down:
	docker compose down -v

cluster:
	bash scripts/resume.sh cluster

resume:
	bash scripts/resume.sh app

status:
	kubectl get nodes -o wide
	kubectl -n $(NS) get pods -o wide

url:
	@curl -s localhost:8080/api/version; echo

reset:
	kubectl delete namespace $(NS) --ignore-not-found --wait=true
	bash scripts/resume.sh app

down:
	kind delete cluster --name quickbite
