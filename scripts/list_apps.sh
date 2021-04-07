ENVIRONMENT=$1
SELECTION=$2

function fail {
    echo "Usage: $(basename $0) ENVIRONMENT SELECTION"
    echo ""
    echo "ENVIRONMENT: [internal-dev|internal-dev-sandbox|internal-qa|internal-qa-sandbox|ref|dev|sandbox|int|prod]"
    echo "SELECTION: [diff|all]"
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


case ${SELECTION} in
    diff)
        # In the case of a release from main, want the diff from the
        # merge commit, i.e. HEAD~ when on a PR want the changes
        # relative to main.
        [ $(git branch --show) == "main" ] && RANGE="HEAD~" || RANGE="origin/main"
        FILES=$(git diff --name-only --diff-filter=A ${RANGE} -- jwks/${ENVIRONMENT}) ;;
    all)
        # If 'all' then just list all files in the environment
        FILES=$(find ./jwks/${ENVIRONMENT} -iname '*.json' -type f -printf '%f\n' || true) ;;
    *)
        fail  ;;
esac



UUID4_REGEX="[0-9a-z]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[ab89][0-9a-f]{3}-[0-9a-f]{12}"
# print all files w/ a UUID regex. || true to supress as no-match case
# as error
echo "${FILES}" | grep -Po "${UUID4_REGEX}" || true
