const express = require("express");
const { body } = require("express-validator");

const modelController = require("../controllers/modelController");
const isAuth = require("../middleware/is-auth");

const router = express.Router();

// POST /model/promptWithMaskedImage
router.post(
  "/promptWithMaskedImage",
  [
    body("chatId").trim().not().isEmpty().withMessage("Please enter a chatId"),
    body("prompt").trim().not().isEmpty().withMessage("Please enter a prompt"),
    body("image").trim().not().isEmpty().withMessage("Please upload an image"),
    body("maskedImage").trim().not().isEmpty().withMessage("Please upload a maskedImage"),
  ],
  isAuth,
  modelController.promptWithMaskedImage
);

// POST /model/getSimilarProducts
router.post(
  "/getSimilarProducts",
  [
    body("image").trim().not().isEmpty().withMessage("Please upload an image"),
  ],
  isAuth,
  modelController.getSimilarProducts
);

router.post(
  "/recommendation",
  [
    body("prompt").trim().not().isEmpty().withMessage("Please enter a prompt"),
    body("products").isArray().withMessage("Please add atleast one product"),
    body("image").trim().not().isEmpty().withMessage("Please upload an image"),
    body("maskedImage").trim().not().isEmpty().withMessage("Please upload an masked image"),
  ],
  isAuth,
  modelController.recommendations
)

module.exports = router;
