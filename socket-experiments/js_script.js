function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function run() {
    await sleep(1)
    return `6*7=${6 * 7}`;
}

module.exports = {
    run
};