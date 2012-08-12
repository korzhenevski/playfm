build:
	@echo "build protofiles"
	@cd proto; protoc ./*.proto --python_out=../rvlib
	@ls -la ./rvlib/*_pb2.py

publish:
	@python setup.py register -r local sdist upload -r local
