const express = require("express");
const { body } = require("express-validator");

const dataController = require("../controllers/dataController");
const isAuth = require("../middleware/is-auth");

const router = express.Router();

// GET /data/new-chat
router.get("/new-chat", isAuth, dataController.getNewChat);

// GET /data/all-chats
router.get("/all-chats", isAuth, dataController.getAllChats);

// GET /data/chat/:chatId
router.get("/chat/:chatId", isAuth, dataController.getChat);

module.exports = router;