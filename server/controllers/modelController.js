const { validationResult } = require("express-validator");
const axios = require("axios").default;

const User = require("../models/User");
const Chat = require("../models/Chat");
const Prompt = require("../models/Prompt");

exports.promptWithMaskedImage = async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      const error = new Error("Enter non-empty prompt and image");
      error.statusCode = 403;
      error.data = errors.array();
      throw error;
    }

    const chatId = req.body.chatId;
    const prompt = req.body.prompt;
    const image = req.body.image;
    const maskedImage = req.body.maskedImage;

    const response = await axios.post(
      process.env.MODEL_API_URL + "/text-masked-image-to-image",
      {
        prompt: prompt,
        image: image,
        masked_image: maskedImage,
      }
    );

    const newPrompt = new Prompt({
      prompt: prompt,
      timestamp: Date.now(),
      image: process.env.BACKEND_URL + "/image/" + response.data.filename,
    });

    await newPrompt.save();

    await Chat.updateOne(
      { _id: chatId },
      { $push: { messages: newPrompt._id } },
      {
        $set: {
          recentImage:
            process.env.BACKEND_URL + "/image/" + response.data.filename,
        },
      }
    );

    // Check if the user contains chat else add
    await User.updateOne({ _id: req.userId }, { $addToSet: { chats: chatId } });

    res.status(200).json({
      message: "Image generated successfully",
      image: process.env.BACKEND_URL + "/image/" + response.data.filename,
    });
  } catch (err) {
    if (!err.statusCode) {
      err.statusCode = 500;
    }
    next(err);
  }
};

exports.getSimilarProducts = async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      const error = new Error("Enter non-empty prompt and image");
      error.statusCode = 403;
      error.data = errors.array();
      throw error;
    }

    const image = req.body.image;

    const response = await axios.post(
      process.env.MODEL_API_URL + "/get-similar-products",
      {
        image: image,
      }
    );

    res.status(200).json({
      message: "Similar products generated successfully",
      products: response.data.products,
    });
  } catch (err) {
    if (!err.statusCode) {
      err.statusCode = 500;
    }
    next(err);
  }
};

exports.recommendations = async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      const error = new Error("Enter non-empty product list, masked image and image");
      error.statusCode = 403;
      error.data = errors.array();
      throw error;
    }

    const prompt = req.body.prompt;
    let products = req.body.products;
    const image = req.body.image;
    const maskedImage = req.body.maskedImage;

    products=products.filter(item => item !== "");

    const response = await axios.post(
      process.env.MODEL_API_URL + "/recommendation",
      {
        prompt: prompt,
        products: products,
        image: image,
        masked_image: maskedImage
      }
    );

    res.status(200).json({
      message: "Image generated successfully",
      image: process.env.BACKEND_URL + "/image/" + response.data.filename,
    });
  } catch (err) {
    if (!err.statusCode) {
      err.statusCode = 500;
    }
    next(err);
  }
}