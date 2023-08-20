const mongoose = require('mongoose');
const Schema = mongoose.Schema;

const promptSchema = new Schema({
    prompt: {
        type: String,
        required: true
    },
    timestamp: {
        type: String,
        required: true
    },
    image: {
        type: String,
    }
});

module.exports = mongoose.model('Prompt', promptSchema);