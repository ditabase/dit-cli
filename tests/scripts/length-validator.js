const PAYLOAD = '7 mm';

function validate() {
    //Begin non-generated code
    function isNumeric(n) {
        return !isNaN(parseFloat(n)) && isFinite(n);
    }

    if (PAYLOAD.indexOf(' ') === -1) {
        return `"${PAYLOAD}" was missing a space separator.`;
    }

    const number = PAYLOAD.substring(0, PAYLOAD.indexOf(' '));

    if (!isNumeric(number)) {
        return `Number field "${number}" was not a number.`;
    }

    if (number < 0) {
        return `Number field "${number}" cannot be negative.`;
    }

    const units = PAYLOAD.substring(PAYLOAD.indexOf(' ') + 1);

    if (units === "") {
        return `Units field "${units}" was blank.`
    }

    return true;
    //End non-generated code
}

console.log(`begin--${validate()}--end`);