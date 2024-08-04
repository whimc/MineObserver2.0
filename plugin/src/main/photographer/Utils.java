package edu.whimc.photographer;

import org.bukkit.ChatColor;
import org.bukkit.command.CommandSender;

public final class Utils {

    public static void msg(CommandSender sender, String... messages) {
        for (String message : messages) {
            sender.sendMessage(color(message));
        }
    }

    public static String color(String str) {
        return ChatColor.translateAlternateColorCodes('&', str);
    }

    public static int parseInt(String input, int defaultValue) {
        Integer parsed = parseInt(input);
        return parsed == null ? defaultValue : parsed;
    }

    public static Integer parseInt(String str) {
        try {
            return Integer.parseInt(str);
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
