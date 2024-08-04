package edu.whimc.photographer;

import com.corundumstudio.socketio.SocketIOClient;
import edu.whimc.observations.models.Observation;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import org.apache.commons.lang.StringUtils;
import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;

public class PhotographerCommand implements CommandExecutor, TabCompleter {

    private final Photographer plugin;

    public PhotographerCommand(Photographer plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!sender.hasPermission("whimc-photographer.admin")) {
            sender.sendMessage(ChatColor.RED + "No permission!");
            return true;
        }

        if (args.length == 0) {
            sendUsage(sender);
            return true;
        }

        String subCmd = args[0];

        if (subCmd.equalsIgnoreCase("clients")) {
            Utils.msg(sender, "&b&lClients:");
            for (SocketIOClient client : this.plugin.getSocketServer().getAllClients()) {
                Utils.msg(sender, "> &b" + client.get("uuid"));
                Utils.msg(sender, "|  IP: &b" + client.getRemoteAddress());
                CameraOperator.getCameraOperator(client.get("uuid")).ifPresentOrElse(
                        co -> Utils.msg(sender, "|  Player: &b" + co.getPlayer().getName() + " &7("
                                + (co.isAvailable() ? "&aAvailable" : "&cBusy") + "&7)"),
                        () -> Utils.msg(sender, "|  Player: &8" + "N/A"));
            }
            return true;
        }

        if (subCmd.equalsIgnoreCase("queue-list")) {
            Utils.msg(sender, "&b&lQueued observations:");
            for (Observation observation : this.plugin.getObservationQueue()) {
                Utils.msg(sender, observation.toString());
            }
            return true;
        }

        if (subCmd.equalsIgnoreCase("queue-clear")) {
            int numCleared = this.plugin.getObservationQueue().size();
            this.plugin.getObservationQueue().clear();
            Utils.msg(sender, "&aCleared " + numCleared + " queued observations");
            return true;
        }

        if (subCmd.equalsIgnoreCase("queue-remove")) {
            if (args.length < 2) {
                Utils.msg(sender, "&o/photographer queue-remove <id>");
                return true;
            }

            String obs_id = args[1];
            boolean removed = this.plugin.getObservationQueue().removeIf(obs -> String.valueOf(obs.getId()).equals(obs_id));
            if (removed) {
                Utils.msg(sender, "&aRemoved observation " + obs_id + " from the queue");
            } else {
                Utils.msg(sender, "&cNo observation with id " + obs_id + " found in queue");
            }

            return true;
        }

        if (subCmd.equalsIgnoreCase("queue-add")) {
            if (args.length < 2) {
                Utils.msg(sender, "&o/photographer queue-add <start id> [end id]");
                return true;
            }

            // Parse start/end observation IDs
            Integer startId = Utils.parseInt(args[1]);
            Integer endId = args.length >= 3 ? Utils.parseInt(args[2]) : startId;
            if (startId == null || endId == null) {
                Utils.msg(sender, "&cCould not parse arguments are integers!");
                return true;
            }

            // Queue up observations to be photographed
            List<Observation> observations = Observation.getObservations().stream()
                    .filter(obs -> obs.getId() >= startId && obs.getId() <= endId)
                    .collect(Collectors.toList());
            for (Observation obs : observations) {
                if (sender instanceof Player) {
                    obs.getHologram().getVisibilityManager().hideTo((Player) sender);
                }
                this.plugin.queueObservationPhotograph(obs);
            }
            Utils.msg(sender, "&aQueueing &2" + observations.size() + " &aobservation(s) to be photographed!");
            return true;
        }

        if (subCmd.equalsIgnoreCase("disconnect-all")) {
            this.plugin.getSocketServer().getAllClients().forEach(client -> {
                sender.sendMessage("Disconnecting " + client.getRemoteAddress() + ": " + client.get("uuid"));
                CameraOperator.getCameraOperator(client.get("uuid")).ifPresent(CameraOperator::unregister);
                client.disconnect();
            });
            return true;
        }

        if (subCmd.equalsIgnoreCase("stop-collecting")) {
            if (!(sender instanceof Player)) {
                sender.sendMessage(ChatColor.RED + "Must be a player!");
                return true;
            }
            CameraOperator.getCameraOperator(((Player) sender).getUniqueId()).ifPresentOrElse(
                    CameraOperator::unregister,
                    () -> sender.sendMessage("You are not a photographer!"));
            return true;
        }

        if (args.length < 2) {
            return true;
        }

        UUID uuid;
        try {
            uuid = UUID.fromString(args[1]);
        } catch (IllegalArgumentException exc) {
            sender.sendMessage("Invalid UUID");
            return true;
        }
        Optional<SocketIOClient> clientOpt = this.plugin.getClient(uuid);

        if (!clientOpt.isPresent()) {
            sender.sendMessage("Client not found");
            return true;
        }

        SocketIOClient client = clientOpt.get();

        if (subCmd.equalsIgnoreCase("disconnect")) {
            sender.sendMessage("Disconnecting " + client.getRemoteAddress() + ": " + client.get("uuid"));
            CameraOperator.getCameraOperator(client.get("uuid")).ifPresent(CameraOperator::unregister);
            client.disconnect();
            return true;
        }

        if (subCmd.equalsIgnoreCase("collect")) {
            if (!(sender instanceof Player)) {
                sender.sendMessage(ChatColor.RED + "You have to be a player");
                return true;
            }
            Player player = (Player) sender;

            Optional<CameraOperator> camera = CameraOperator.registerCameraOperator(this.plugin, player, client);
            if (camera.isPresent()) {
                Utils.msg(player, "&aYou have become a photographer for " + client.get("uuid"));
                Utils.msg(player, "&7There are &f&l" + this.plugin.getObservationQueue().size() +
                        "&7 queued observations");
            } else {
                player.sendMessage(ChatColor.RED + "You are already collecting or that client is in use");
            }

            return true;
        }

        if (subCmd.equalsIgnoreCase("send")) {
            if (args.length <= 2) {
                sender.sendMessage(ChatColor.ITALIC + "/photographer send <uuid> <msg>");
                return true;
            }

            String message = StringUtils.join(args, " ", 2, args.length);
            Bukkit.getScheduler().runTaskAsynchronously(this.plugin, () ->
                    client.sendEvent("message", message)
            );
            return true;
        }

        sendUsage(sender);
        return true;
    }

    private void sendUsage(CommandSender sender) {
        Utils.msg(sender,
                "&e/photographer &6clients",
                "&e/photographer &6queue-list",
                "&e/photographer &6queue-clear",
                "&e/photographer &6queue-remove &7<id>",
                "&e/photographer &6queue-add &7<start id> [end id]",
                "&e/photographer &6disconnect-all",
                "&e/photographer &6collect &7<uuid>",
                "&e/photographer &6stop-collecting",
                "&e/photographer &6disconnect &7<uuid>",
                "&e/photographer &6send &7<uuid> <msg>"
        );
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (args.length <= 1) {
            return Stream.of(
                            "clients",
                            "queue-list",
                            "queue-clear",
                            "queue-remove",
                            "queue-add",
                            "disconnect-all",
                            "collect",
                            "stop-collecting",
                            "disconnect",
                            "send"
                    ).filter(arg -> arg.startsWith(args[0].toLowerCase()))
                    .collect(Collectors.toList());
        }
        if (args[0].equalsIgnoreCase("queue-add")) {
            int minObs = args.length > 2 ? Utils.parseInt(args[1], 0) : 0;
            return Observation.getObservations().stream()
                    .filter(obs -> obs.getId() > minObs)
                    .map(obs -> Integer.toString(obs.getId()))
                    .sorted()
                    .collect(Collectors.toList());
        }
        return this.plugin.getSocketServer().getAllClients().stream()
                .map(client -> client.get("uuid").toString())
                .collect(Collectors.toList());
    }

}
