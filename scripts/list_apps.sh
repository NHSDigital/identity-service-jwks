ENVIRONMENT=$1

function fail {
    echo "Usage: $(basename $0) ENVIRONMENT"
    echo ""
    echo "ENVIRONMENT: [internal-dev|internal-dev-sandbox|internal-qa|internal-qa-sandbox|ref|dev|sandbox|int|prod]"
    echo "Note: should be invoked from identity-service-jwks directory"
    exit 1
}

case ${ENVIRONMENT} in
    internal-dev)         ;;
    internal-dev-sandbox) ;;
    internal-qa)          ;;
    internal-qa-sandbox)  ;;
    ref)                  ;;
    dev)                  ;;
    sandbox)              ;;
    int)                  ;;
    prod)                 ;;
    *)               fail ;;
esac

if [[ ! -d ./jwks/${ENVIRONMENT} ]]; then
    # valid environment, but no directory
    # exit without error
    exit 0
fi


FILES=$(find ./jwks/${ENVIRONMENT} -iname '*.json' -type f -printf '%f\n' || true)

UUID4_REGEX="[0-9a-z]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[ab89][0-9a-f]{3}-[0-9a-f]{12}"
# print all files w/ a UUID regex. || true to supress as no-match case
# as error
echo "${FILES}" | grep -Po "${UUID4_REGEX}" || true
