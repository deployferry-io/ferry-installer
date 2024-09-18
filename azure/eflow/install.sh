while getopts k: flag
do
    case "${flag}" in
        k) KEY=${OPTARG};;
    esac
done
echo $KEY

/usr/bin/python3 install.py $KEY

iotedge config apply