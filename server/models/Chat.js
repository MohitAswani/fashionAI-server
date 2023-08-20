const mongoose = require('mongoose');
const Schema = mongoose.Schema;

const chatSchema = new Schema({
    prompts: [{
        type: Schema.Types.ObjectId,
        ref: 'Prompt'
    }],
    recentImage: {
        type: String,
    },
});

module.exports = mongoose.model('Chat', chatSchema);