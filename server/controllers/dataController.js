const User = require("../models/User");
const Chat = require("../models/Chat");
const Prompt = require("../models/Prompt");

exports.getNewChat = async (req, res, next) => {
  try {
    const userId = req.userId;

    const newChat = new Chat({
      prompts: [],
      recentImage: "",
    });

    await newChat.save();

    await User.updateOne(
      { _id: userId },
      { $addToSet: { chats: newChat._id } }
    );

    res.status(200).json({
      message: "New chat created successfully",
      chatId: newChat._id,
    });
  } catch (err) {
    if (!err.statusCode) {
      err.statusCode = 500;
    }
    next(err);
  }
};

exports.getAllChats = async (req, res, next) => {
  try {
    const userId = req.userId;

    const chats = await User.findById(userId).populate("chats");

    res.status(200).json({
      message: "Chats fetched successfully",
      chats: chats.chats,
    });
  } catch (err) {
    if (!err.statusCode) {
      err.statusCode = 500;
    }
    next(err);
  }
};

exports.getChat = async (req, res, next) => {
  try {
    const chatId = req.params.chatId;
    const chat = await Chat.findById(chatId);

    res.status(200).json({
      message: "Chat fetched successfully",
      chat: chat,
    });
  } catch (err) {
    if (!err.statusCode) {
      err.statusCode = 500;
    }
    next(err);
  }
};
