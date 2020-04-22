function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function run() {
    await sleep(1)
    return `pi=${Math.round(Math.PI * 10000) / 10000}`;
}

module.exports = {
    run
};