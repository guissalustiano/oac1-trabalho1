docker build -t oac1-t1 .
docker run -it --privileged --rm -v $PWD/src:/app -w /app oac1-t1
